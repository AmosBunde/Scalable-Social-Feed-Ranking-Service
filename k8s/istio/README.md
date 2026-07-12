# Istio Service Mesh Configuration

Istio traffic-management and security policy for the `social-feed`
namespace (issue #18). Layout:

| File | Contents |
| --- | --- |
| `gateway.yaml` | Ingress `Gateway` (port 80, explicit host `feed.example.com`) fronting `api-gateway` |
| `virtual-services.yaml` | One `VirtualService` per service: retries (3 attempts) and timeouts (3s ranking-engine, 5s feed-service, 3s user-profile, 5s content-ingestion, 10s edge) |
| `destination-rules.yaml` | One `DestinationRule` per service: `ISTIO_MUTUAL` TLS, connection pools, outlier detection (circuit breaking), `stable`/`canary` subsets for ranking-engine |
| `peer-authentication.yaml` | Namespace-wide `STRICT` mTLS |
| `authorization-policies.yaml` | Default-deny plus per-service ALLOW rules keyed on mTLS principals |
| `service-accounts.yaml` | Dedicated ServiceAccount per workload (SPIFFE identity) |
| `ranking-engine-canary.yaml` | Opt-in canary deployment + 90/10 traffic split (not applied by default) |
| `kiali/kiali-deployment.yaml` | Kiali dashboard for mesh observability |

## Prerequisites

- Istio >= 1.20 installed (`istioctl install --set profile=default`),
  which provides the `istio-ingressgateway` in `istio-system`.
- The workloads from `k8s/base` (or an overlay) deployed to `social-feed`.

## Enabling sidecar injection

Sidecar injection is **label-driven per namespace**. The `social-feed`
namespace defined in `k8s/base/deployments.yaml` already carries the label:

```yaml
metadata:
  name: social-feed
  labels:
    istio-injection: enabled
```

To enable it on an existing cluster (or another namespace):

```bash
kubectl label namespace social-feed istio-injection=enabled --overwrite
```

Injection only happens at pod creation, so restart workloads that were
running before the label was applied:

```bash
kubectl rollout restart deployment -n social-feed
kubectl get pods -n social-feed   # expect 2/2 READY (app + istio-proxy)
```

To exclude a single workload, annotate its pod template with
`sidecar.istio.io/inject: "false"` (the Kiali deployment does this).

## Applying the mesh configuration

```bash
kubectl apply -k k8s/base      # workloads (or use an overlay)
kubectl apply -k k8s/istio     # mesh policy + Kiali
```

Verify:

```bash
istioctl analyze -n social-feed
istioctl x describe pod <api-gateway-pod> -n social-feed
```

## mTLS

`peer-authentication.yaml` enforces `STRICT` mTLS namespace-wide: sidecars
reject any plaintext traffic. `destination-rules.yaml` sets
`ISTIO_MUTUAL` on the client side so every hop is mutually authenticated.
Kubelet HTTP probes keep working because Istio rewrites them to the
pilot-agent.

## Authorization

`authorization-policies.yaml` starts from default-deny and only allows:

```
istio-ingressgateway -> api-gateway:8000
api-gateway          -> feed-service:8001, user-profile:8003
feed-service         -> ranking-engine:8002, user-profile:8003, content-ingestion:8004
```

Every workload runs under a dedicated ServiceAccount
(`service-accounts.yaml`; `k8s/base/deployments.yaml` sets
`serviceAccountName`), so each rule authorizes callers by mTLS principal
(e.g. `cluster.local/ns/social-feed/sa/api-gateway`) — a compromised pod
elsewhere in the namespace gets no implicit access.

## Canary rollout for ranking-engine

`ranking-engine-canary.yaml` is excluded from `kustomization.yaml` because
its `VirtualService` replaces the default `ranking-engine` route with a
weighted 90/10 split across the `stable`/`canary` subsets defined in
`destination-rules.yaml`.

1. Label the stable pods so the `stable` subset matches them:

   ```bash
   kubectl patch deployment ranking-engine -n social-feed --type merge \
     -p '{"spec":{"template":{"metadata":{"labels":{"version":"stable"}}}}}'
   ```

2. Start the canary (deployment + 90/10 split):

   ```bash
   kubectl apply -f k8s/istio/ranking-engine-canary.yaml
   ```

3. Watch error rate and latency per subset in Kiali (or Prometheus), then
   promote by shifting weights (90/10 -> 50/50 -> 0/100) and rolling the
   canary image into the stable deployment.

4. Roll back instantly by restoring the default route:

   ```bash
   kubectl apply -f k8s/istio/virtual-services.yaml
   kubectl delete deployment ranking-engine-canary -n social-feed
   ```

## Kiali dashboard

Kiali runs in `istio-system` with `token` auth. Port-forward, then log
in with a ServiceAccount token:

```bash
kubectl port-forward svc/kiali -n istio-system 20001:20001
kubectl create token kiali-viewer -n istio-system   # paste into the login form
```

Then open <http://localhost:20001/kiali>. The Graph view shows live
traffic between social-feed services, mTLS lock icons on each edge, and
the applied VirtualService/DestinationRule config per workload.

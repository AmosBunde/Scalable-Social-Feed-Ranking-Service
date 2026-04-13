# ADR 006: Istio Service Mesh with Kiali

## Status
Accepted

## Context
Production deployment needs mTLS between services, traffic management (canary deployments, circuit breaking), distributed tracing correlation, and a service topology dashboard.

## Decision
Use Istio 1.21+ with automatic sidecar injection in the social-feed namespace. Kiali for service mesh observability. VirtualService and DestinationRule resources for traffic policies.

## Consequences
- **Positive**: Zero-config mTLS, traffic splitting for A/B model rollout, retry and timeout policies at mesh level, Kiali provides real-time service graph.
- **Negative**: ~10% latency overhead from Envoy sidecar proxies. Memory overhead per pod (~50MB). Operational complexity.
- **Mitigated**: Overhead is acceptable given the latency budget (50ms for cached feeds). Istio profile=production minimizes resource usage. Kiali dashboard reduces debugging time.

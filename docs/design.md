# Design

The extraction path is:

```text
raw text -> candidate spans -> normalized skill -> source concept -> ten-category mapping -> bundle metrics
```

The baseline uses a versioned public seed dictionary. Optional neural models are future candidate generators and must not silently change the baseline's source of truth. Mapping uncertainty is explicit; the system can return `NIL`.


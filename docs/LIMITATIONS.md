# Interpretation and reproducibility limits

- **Selected tasks and cuts.** Full-150 and Hard-45 answer different questions.
  Hard-45 was selected for difficulty and shares 26 environments with Full-150.
  Its exploit rates are selection-amplified.
- **Single draws and resampling.** Several headline rows use one generated rubric.
  Resampling was characterized for only a subset of generators; do not transfer
  those intervals to other models or treat small ordering differences as resolved.
- **Attacker dependence.** Rates measure exploitation under a specified attacker,
  judge and oracle chain. They do not certify a global optimum or adversarial bound.
- **Shared families and self-play.** Some generator/attacker/oracle roles share a
  model family, and the Opus 5 arm uses the model in three roles. Held-out checks
  bound particular explanations without establishing fully independent evaluators.
- **Oracle and source limits.** A certificate is a task-specific operational
  honesty boundary. Human calibration used a single author/rater; agreement does
  not make the oracle infallible. Source-verification labels and mechanical schema
  checks do not establish semantic truth.
- **Historical execution conditions.** Original runs used an author-specific
  agent workflow runtime. Audit records describe tool access, some access to
  repository/ground-truth information, certificate/configuration changes and
  invalidated attempts. This candidate excludes internal logs but does not claim
  those conditions never occurred. New evaluations should explicitly isolate
  role inputs and record tool permissions.
- **Missing records and incomplete runs.** Not every original headline draw can
  be regenerated from a saved rubric; some bridge or experimental stages were
  stopped or invalidated. The included census is limited to its named completed
  result inputs and must not be described as reproducing every paper result.
- **Statistical interpretation.** The research notes identify unresolved wording
  around multiple testing, non-significance, mean shifts versus variance and
  single-draw conclusions. Packaging does not resolve those questions or modify
  the recorded measurements.

The benchmark is an adversarial evaluation of generated reward specifications.
The worked example is not a measurement of a policy's reinforcement-learning
training trajectory. Ordinary best-of-N selection and adversarial optimization
are different threat models.

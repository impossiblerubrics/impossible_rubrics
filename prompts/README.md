# Reference prompts

These are readable templates, not a model API runner. Replace bracketed sections
with the intended role inputs, preserving a record of exactly what you sent.
`generator.txt` follows the neutral generator instruction in the paper. The
other templates describe the required role boundaries; historical arms contain
prompt variants and are not reproduced by a claim of template equivalence.

An environment file contains private-to-role evaluation annotations. Use
`export_inputs.py` for generator inputs and the input contracts in
`docs/EVALUATION.md` when assembling attacker, judge and oracle prompts.
Do not give the generator the certificate, gold answers, difficulty tier, known
failure modes, review notes or evidence relevance annotations.

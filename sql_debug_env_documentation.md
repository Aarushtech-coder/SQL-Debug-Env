# SQL Debug Environment Documentation

This project is an OpenEnv-compatible SQL debugging benchmark. It exposes a
SQLite-backed environment where agents repair broken SQL queries and receive
structured feedback.

## Primary Evaluation Surface

The strongest, most reliable parts of the project are:

- `SQLDebugEnv` in `environment.py`
- static task suites in `tasks/`
- multi-step command wrapper in `multi_step_env.py`
- grader in `grader.py`
- FastAPI app in `main.py`
- deterministic no-key baseline in `local_solver.py`

## Demo Strategy

For judging, run this sequence:

1. Start the server with `python main.py`.
2. Open `/docs` and show `/tasks`, `/reset`, `/step`, and `/grader`.
3. Run `python baseline/run_baseline.py` without API keys to prove the
   environment and grader work.
4. Add `GROQ_API_KEY` or `OPENAI_API_KEY` and rerun the baseline to show the LLM
   path.
5. Optionally open the Streamlit dashboard for a visual walkthrough.

## Honest Scope

The adversarial generator and RL fine-tuning hooks are experimental extensions.
They show where the project can go next, but they are not the core claim of the
current implementation.

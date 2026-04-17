"""
Repository root entrypoint. Equivalent to: python -m app.main
"""
import runpy

runpy.run_module("app.main", run_name="__main__", alter_sys=True)

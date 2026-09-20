"""The energy manifest's own honesty: a row is measured, or it says it is not.

The sweep behind this manifest is a two-and-a-half hour render, so the staleness check has to be exactly
right in both directions. A row that reads fresh over changed pixels is the failure the hash exists to
catch; a row that cries stale when nothing about the picture moved is the failure that gets the check
ignored, and this repository has recorded both.
"""


def test_one_shots_ground_row_does_not_stale_every_other_shots_energy():
    """`runtime/shotLuma.ts` is a per-register TABLE that every reader imports whole, so registering a new
    shot — or re-measuring one shot's ground — used to rewrite it and mark every other reader's energy row
    stale, with nothing about their pictures changed. A sweep is a two-and-a-half hour render, so a check
    that cries wolf there gets answered by re-measuring the library or by ignoring it. A reader depends on
    the file's CODE plus its OWN row, and that is what the hash covers."""
    import importlib.util
    import os
    import tempfile
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location(
        "register_energy", os.path.join(os.path.dirname(here), "scripts", "register_energy.py"))
    re_ = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(re_)

    base = ("export type Lum = 'dark' | 'mid' | 'light';\n"
            "export const SHOT_LUMA: Record<string, Lum> = {\n"
            "  Alpha: 'dark',\n"
            "  Beta: 'light', Gamma: 'mid',\n"
            "};\n"
            "export const groundOf = (id: string) => SHOT_LUMA[id] ?? 'dark';\n")
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "shotLuma.ts")
        open(p, "w", encoding="utf-8").write(base)
        alpha_before = re_._dep_bytes(p, "Alpha")
        # ANOTHER register's row changes, and a fourth is registered
        open(p, "w", encoding="utf-8").write(
            base.replace("Beta: 'light'", "Beta: 'dark'").replace("  Alpha: 'dark',\n",
                                                                  "  Delta: 'mid',\n  Alpha: 'dark',\n"))
        assert re_._dep_bytes(p, "Alpha") == alpha_before, "another shot's ground row staled Alpha"
        # ...and Alpha's OWN row still does
        open(p, "w", encoding="utf-8").write(base.replace("Alpha: 'dark'", "Alpha: 'light'"))
        assert re_._dep_bytes(p, "Alpha") != alpha_before, "Alpha's own ground row no longer affects its hash"
        # the file's CODE still does, for every reader
        open(p, "w", encoding="utf-8").write(base.replace("?? 'dark'", "?? 'light'"))
        assert re_._dep_bytes(p, "Alpha") != alpha_before, "a change to the module's code no longer stales it"

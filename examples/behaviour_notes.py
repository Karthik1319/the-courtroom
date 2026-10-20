# Normal-behaviour test for the notes app (Round 0 baseline).
# It must pass on the ORIGINAL code — it proves the app's legitimate feature
# works, so a patch that breaks it can be rejected. The harness runs this
# after writing the app to target_app.py; exit 0 = pass.
import target_app

app = target_app.NotesApp()
# alice can read her own note (seeded by _init_db at id=1)
assert app.get_note(1, "alice").startswith("Grocery"), "alice should read her own note"
print("behaviour OK")

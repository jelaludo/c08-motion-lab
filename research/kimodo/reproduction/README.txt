Owned helper snapshots for the separate Kimodo workspace.
Restore these helpers into that workspace tools/ directory; their ROOT convention expects its outputs, upstream install, model access and original robot asset workspace. They are research snapshots, not a standalone hosted inference service.
Pin versions from publication.json and the dev log. Use official Kimodo installation and model access instructions. Do not copy tokens or model caches into this repo.
The current game plan includes its generated numeric jump anchors under game-derived/constraints; copy that folder to the separate workspace root. Public playback reproduction instead uses assets-manifest.json, exact animation tracks, shared character assets, expected source joint samples and the public validation script.
The Meshy body retains its own CC BY attribution. Source motion quality and downstream engine acceptance are separate checks.

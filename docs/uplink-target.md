# Uplink target notes

## Why Uplink first

Half-Life: Uplink is a compact three-map campaign (`hldemo1`, `hldemo2`, `hldemo3`). That gives the N64 port a finite first-gameplay target while still exercising the systems that matter: BSP loading, GoldSrc entities, textures/lightmaps, models, sound, scripted sequences, combat, save/map transitions, and HLSDK game code.

## Data policy

The project repository/ROM contains no Valve game assets. Local tooling prepares the original Uplink demo into the SummerCart SD layout and copies the **whole recovered game-data tree** unchanged. The original `pak0.PAK` remains intact; `hldemo1/2/3` are only validation markers that prove the correct Uplink data was found. The prep process records hashes so hardware reports can be tied to the exact local data used.

## First playable definition

A revision is not called "playable Uplink" merely because it parses a BSP. The milestone requires:

- `hldemo1.bsp` rendered on real N64 hardware;
- player spawn and analog movement;
- collision and basic entity/game-DLL execution;
- enough audio to validate the sound path;
- successful transition into `hldemo2.bsp` and `hldemo3.bsp` without exceeding 8 MiB.

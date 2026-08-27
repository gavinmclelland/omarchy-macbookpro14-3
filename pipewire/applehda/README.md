# AppleHDA layouts (Intel CS8409)

Source: macOS `AppleHDA.kext/Contents/Resources/layoutN.xml.zlib` on this
machine’s APFS System volume. **Do not commit the kext.**

`parse_layout.py` inflates those files and dumps `DspEqualization32` biquads
(taprobane99’s mapping from [davidjo#179](https://github.com/davidjo/snd_hda_macbookpro/issues/179)).

```bash
python3 parse_layout.py raw -o parsed.json
```

Filter types: 0 low-pass, 1 high-pass, 4 bell, 6 notch.
Roles: WooferSym/Asym, TweeterSym/Asym, Global_PreEQ.

A software peak limiter (not `speakersafetyd`) belongs on this graph: 14,3
amps are MAX98706, no V/ISENSE.

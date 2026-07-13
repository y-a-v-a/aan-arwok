# On Kawara font face

Tracing a lot of images of "date paintings" from On Kawara's "Today" series, I've created a font
as complete as possible. I couldn't find images with a "H", "Q", "W" or "X" so those will be
designed in relation to the available letters.

Originally made with Glyphs Mini; now built and kerned with an open-source toolchain
(glyphsLib + ufo2ft + fontTools) — Glyphs Mini is no longer needed. `kawara2.glyphs`
is the source of truth; `OnKawara-Regular.otf` is compiled from it.

https://glyphsapp.com/tutorials/kerning
https://www.schoolofmotion.com/blog/custom-font-illustrator-fontforge

## Building the font

One-time setup (needs Python 3):

    make setup

Compile `kawara2.glyphs` to `OnKawara-Regular.otf` (repo root + `www/`), including
all kerning as a GPOS table, and refresh `www/kerning.js`:

    make build

## Kerning workbench

Fine-tune kerning in the browser — no font editor required:

    make kern

then open <http://localhost:8765/kern.html>. Type any sample text (or pick a preset),
click between two letters and nudge with the arrow keys (↑/↓ ±10, ⇧ ±50, ⌥ ±1;
←/→ walks through the pairs). "sync case" keeps all four case combinations of a
letter pair identical, since the lowercase glyphs are component copies of the capitals.
Hitting **Save** writes the pairs back into `kawara2.glyphs` and rebuilds the OTF in
place — toggle "font's own kerning" to proof the baked-in result.

Without the local server (e.g. the page hosted statically), **Save** downloads a
`kerning.json` instead; apply it with:

    make apply FILE=kerning.json

Check for pairs whose case combinations disagree:

    make audit

## Color variants

Date painting color variants
white on gray: #f1f1f1 on #383838
white on red: #e2e2e2 on #cd3838
white on greenish: #e2e3e4 on #323b3f

## Glyphs to add

* ?
* !
* -

## Sentences with all alphabet characters

Jack amazed a few girls by dropping the antique onyx vase!
THE QUICK BROWN FOX, JUMPS OVER THE LAZY DOG.

## Kerning helpers

WAVERY HAWAIIAN HAVANA PLYWOOD
VANWAYMAN
DIFFICULT WAFFLES
TAWDY
YEARLY
WATERY
LAVA
WHY FLY
YONDER

AABACADAEAFAGAHAIAJAKALAMANAOAPAQARASATAUAVAWAXAYAZA
ABBBCBDBEBFBGBHBIBJBKBLBMBNBOBPBQBRBSBTBUBVBWBXBYBZB
ACBCCCDCECFCGCHCICJCKCLCMCNCOCPCQCRCSCTCUCVCWCXCYCZC
ADBDCDDDEDFDGDHDIDJDKDLDMDNDODPDQDRDSDTDUDVDWDXDYDZD
AEBECEDEEEFEGEHEIEJEKELEMENEOEPEQERESETEUEVEWEXEYEZE
AFBFCFDFEFFFGFHFIFJFKFLFMFNFOFPFQFRFSFTFUFVFWFXFYFZF
AGBGCGDGEGFGGGHGIGJGKGLGMGNGOGPGQGRGSGTGUGVGWGXGYGZG
AHBHCHDHEHFHGHHHIHJHKHLHMHNHOHPHQHRHSHTHUHVHWHXHYHZH
AIBICIDIEIFIGIHIIIJIKILIMINIOIPIQIRISITIUIVIWIXIYIZI
AJBJCJDJEJFJGJHJIJJJKJLJMJNJOJPJQJRJSJTJUJVJWJXJYJZJ
AKBKCKDKEKFKGKHKIKJKKKLKMKNKOKPKQKRKSKTKUKVKWKXKYKZK
ALBLCLDLELFLGLHLILJLKLLLMLNLOLPLQLRLSLTLULVLWLXLYLZL
AMBMCMDMEMFMGMHMIMJMKMLMMMNMOMPMQMRMSMTMUMVMWMXMYMZM
ANBNCNDNENFNGNHNINJNKNLNMNNNONPNQNRNSNTNUNVNWNXNYNZN
AOBOCODOEOFOGOHOIOJOKOLOMONOOOPOQOROSOTOUOVOWOXOYOZO
APBPCPDPEPFPGPHPIPJPKPLPMPNPOPPPQPRPSPTPUPVPWPXPYPZP
AQBQCQDQEQFQGQHQIQJQKQLQMQNQOQPQQQRQSQTQUQVQWQXQYQZQ
ARBRCRDRERFRGRHRIRJRKRLRMRNRORPRQRRRSRTRURVRWRXRYRZR
ASBSCSDSESFSGSHSISJSKSLSMSNSOSPSQSRSSSTSUSVSWSXSYSZS
ATBTCTDTETFTGTHTITJTKTLTMTNTOTPTQTRTSTTTUTVTWTXTYTZT
AUBUCUDUEUFUGUHUIUJUKULUMUNUOUPUQURUSUTUUUVUWUXUYUZU
AVBVCVDVEVFVGVHVIVJVKVLVMVNVOVPVQVRVSVTVUVVVWVXVYVZV
AWBWCWDWEWFWGWHWIWJWKWLWMWNWOWPWQWRWSWTWUWVWWWXWYWZW
AXBXCXDXEXFXGXHXIXJXKXLXMXNXOXPXQXRXSXTXUXVXWXXXYXZX
AYBYCYDYEYFYGYHYIYJYKYLYMYNYOYPYQYRYSYTYUYVYWYXYYYZY
AZBZCZDZEZFZGZHZIZJZKZLZMZNZOZPZQZRZSZTZUZVZWZXZYZZZ

(c) 2018 ax710.org, y-a-v-a.org

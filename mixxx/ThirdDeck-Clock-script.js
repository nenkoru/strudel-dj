// Third Deck clock: every 40 ms, one SysEx message per loaded deck for the Third Deck page.
// Mixxx exposes no bar or downbeat (mixxxdj/mixxx#5218; the DJ-505 mapping counts beats by hand),
// so this sends the absolute position in the track and the page finds bars and phrases from its
// own analysis of the track (matched by duration); beat_distance covers tracks it does not know.
//
// F0 7D 01 deck play pos_ms(4) bpm*100(3) file_bpm*100(3) duration_ms(4) beat_distance*16383(2) level F7
// (numbers big-endian in 7-bit bytes; level 0-127 = volume fader x crossfader side)
var ThirdDeckClock = {};

ThirdDeckClock.bytes = function(value, n) {
    var out = [];
    var v = Math.max(0, Math.round(value));
    for (var i = n - 1; i >= 0; i--) {
        out.push(Math.floor(v / Math.pow(128, i)) % 128);
    }
    return out;
};

// Linear crossfader curve: enough to tell which deck the room hears.
ThirdDeckClock.side = function(group) {
    var x = engine.getValue("[Master]", "crossfader");
    var o = engine.getValue(group, "orientation");  // 0 left, 1 center, 2 right
    if (o === 0) { return x <= 0 ? 1 : 1 - x; }
    if (o === 2) { return x >= 0 ? 1 : 1 + x; }
    return 1;
};

ThirdDeckClock.send = function() {
    var b = ThirdDeckClock.bytes;
    for (var deck = 1; deck <= 4; deck++) {
        var group = "[Channel" + deck + "]";
        if (!engine.getValue(group, "track_loaded")) { continue; }
        var duration = engine.getValue(group, "duration");
        var level = engine.getValue(group, "volume") * ThirdDeckClock.side(group);
        var msg = [0xF0, 0x7D, 0x01, deck, engine.getValue(group, "play") ? 1 : 0]
            .concat(b(engine.getValue(group, "playposition") * duration * 1000, 4))
            .concat(b(engine.getValue(group, "bpm") * 100, 3))
            .concat(b(engine.getValue(group, "file_bpm") * 100, 3))
            .concat(b(duration * 1000, 4))
            .concat(b(engine.getValue(group, "beat_distance") * 16383, 2))
            .concat([Math.min(127, Math.round(level * 127)), 0xF7]);
        midi.sendSysexMsg(msg, msg.length);
    }
};

ThirdDeckClock.init = function() {
    ThirdDeckClock.timer = engine.beginTimer(40, ThirdDeckClock.send);
};

ThirdDeckClock.shutdown = function() {
    engine.stopTimer(ThirdDeckClock.timer);
};

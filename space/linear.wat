;; out[r] = s[r] * sum_c q[r*m + c] * x[c]: int8 weights (one float32 scale per row) times float32 activations,
;; 16 columns per iteration with f32x4 SIMD. All arguments are byte offsets into the exported memory; m % 16 == 0.
(module
  (memory (export "mem") 1)
  (func (export "linear") (param $q i32) (param $s i32) (param $x i32) (param $out i32) (param $n i32) (param $m i32)
    (local $r i32) (local $c i32) (local $qp i32) (local $xp i32) (local $w v128)
    (local $a0 v128) (local $a1 v128) (local $a2 v128) (local $a3 v128)
    (block $done (loop $rows
      (br_if $done (i32.ge_u (local.get $r) (local.get $n)))
      (local.set $a0 (v128.const i32x4 0 0 0 0)) (local.set $a1 (v128.const i32x4 0 0 0 0))
      (local.set $a2 (v128.const i32x4 0 0 0 0)) (local.set $a3 (v128.const i32x4 0 0 0 0))
      (local.set $qp (i32.add (local.get $q) (i32.mul (local.get $r) (local.get $m))))
      (local.set $xp (local.get $x))
      (local.set $c (i32.const 0))
      (block $cdone (loop $cols
        (br_if $cdone (i32.ge_u (local.get $c) (local.get $m)))
        (local.set $w (v128.load8x8_s (local.get $qp)))
        (local.set $a0 (f32x4.add (local.get $a0) (f32x4.mul
          (f32x4.convert_i32x4_s (i32x4.extend_low_i16x8_s (local.get $w))) (v128.load (local.get $xp)))))
        (local.set $a1 (f32x4.add (local.get $a1) (f32x4.mul
          (f32x4.convert_i32x4_s (i32x4.extend_high_i16x8_s (local.get $w))) (v128.load offset=16 (local.get $xp)))))
        (local.set $w (v128.load8x8_s offset=8 (local.get $qp)))
        (local.set $a2 (f32x4.add (local.get $a2) (f32x4.mul
          (f32x4.convert_i32x4_s (i32x4.extend_low_i16x8_s (local.get $w))) (v128.load offset=32 (local.get $xp)))))
        (local.set $a3 (f32x4.add (local.get $a3) (f32x4.mul
          (f32x4.convert_i32x4_s (i32x4.extend_high_i16x8_s (local.get $w))) (v128.load offset=48 (local.get $xp)))))
        (local.set $qp (i32.add (local.get $qp) (i32.const 16)))
        (local.set $xp (i32.add (local.get $xp) (i32.const 64)))
        (local.set $c (i32.add (local.get $c) (i32.const 16)))
        (br $cols)))
      (local.set $a0 (f32x4.add (f32x4.add (local.get $a0) (local.get $a1)) (f32x4.add (local.get $a2) (local.get $a3))))
      (f32.store (i32.add (local.get $out) (i32.shl (local.get $r) (i32.const 2)))
        (f32.mul (f32.load (i32.add (local.get $s) (i32.shl (local.get $r) (i32.const 2))))
          (f32.add (f32.add (f32x4.extract_lane 0 (local.get $a0)) (f32x4.extract_lane 1 (local.get $a0)))
                   (f32.add (f32x4.extract_lane 2 (local.get $a0)) (f32x4.extract_lane 3 (local.get $a0))))))
      (local.set $r (i32.add (local.get $r) (i32.const 1)))
      (br $rows))))
)

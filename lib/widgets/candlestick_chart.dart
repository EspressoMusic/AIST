import 'dart:math';

import 'package:flutter/material.dart';

/// Single OHLC candle for dummy charting.
class CandlestickDatum {
  const CandlestickDatum({
    required this.open,
    required this.high,
    required this.low,
    required this.close,
  });

  final double open;
  final double high;
  final double low;
  final double close;

  bool get isBullish => close >= open;
}

class DummyCandlePack {
  const DummyCandlePack({
    required this.candles,
    required this.entryIndex,
    this.exitIndex,
  });

  final List<CandlestickDatum> candles;
  final int entryIndex;
  final int? exitIndex;
}

/// Builds reproducible dummy candles around a trade's entry (and optional exit).
DummyCandlePack buildDummyCandlesForTrade({
  required String tradeId,
  required double entryPrice,
  required bool isOpen,
  int count = 42,
  int entryIndex = 26,
}) {
  final rng = Random(tradeId.hashCode.abs());
  final candles = <CandlestickDatum>[];
  var px = entryPrice * (0.985 + rng.nextDouble() * 0.03);

  for (var i = 0; i < count; i++) {
    final drift = (rng.nextDouble() - 0.48) * entryPrice * 0.0028;
    final open = px;
    final close = (px + drift).clamp(entryPrice * 0.92, entryPrice * 1.08);
    final high = max(open, close) + rng.nextDouble() * entryPrice * 0.0015;
    final low = min(open, close) - rng.nextDouble() * entryPrice * 0.0015;
    candles.add(
      CandlestickDatum(open: open, high: high, low: low, close: close),
    );
    px = close;
  }

  if (entryIndex >= 0 && entryIndex < candles.length && entryPrice > 0) {
    final e = candles[entryIndex];
    candles[entryIndex] = CandlestickDatum(
      open: e.open,
      high: max(e.high, entryPrice * 1.001),
      low: min(e.low, entryPrice * 0.999),
      close: entryPrice,
    );
  }

  int? exitIdxResolved;
  if (!isOpen && candles.length > entryIndex + 3) {
    final exitIdx = min(candles.length - 2, entryIndex + 9 + rng.nextInt(6));
    final target =
        candles[exitIdx].close * (1 + (rng.nextDouble() - 0.5) * 0.004);
    final c = candles[exitIdx];
    candles[exitIdx] = CandlestickDatum(
      open: c.open,
      high: max(max(c.open, target), c.high),
      low: min(min(c.open, target), c.low),
      close: target,
    );
    exitIdxResolved = exitIdx;
  }

  return DummyCandlePack(
    candles: candles,
    entryIndex: entryIndex,
    exitIndex: exitIdxResolved,
  );
}

/// Japanese candlesticks with optional entry/exit column markers.
class CandlestickChart extends StatelessWidget {
  const CandlestickChart({
    super.key,
    required this.candles,
    required this.timeframeLabel,
    this.entryIndex,
    this.exitIndex,
    this.height = 220,
  });

  final List<CandlestickDatum> candles;
  final String timeframeLabel;
  final int? entryIndex;
  final int? exitIndex;
  final double height;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Chip(
              label: Text(timeframeLabel),
              visualDensity: VisualDensity.compact,
              backgroundColor: scheme.surfaceContainerHighest,
              labelStyle: TextStyle(
                color: scheme.onSurfaceVariant,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        SizedBox(
          height: height,
          width: double.infinity,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: CustomPaint(
              painter: _CandlestickPainter(
                candles: candles,
                entryIndex: entryIndex,
                exitIndex: exitIndex,
                bullColor: const Color(0xFF22C55E),
                bearColor: const Color(0xFFEF4444),
                gridColor: scheme.outlineVariant.withValues(alpha: 0.35),
                bgColor: scheme.surfaceContainerHighest.withValues(alpha: 0.45),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _CandlestickPainter extends CustomPainter {
  _CandlestickPainter({
    required this.candles,
    required this.bullColor,
    required this.bearColor,
    required this.gridColor,
    required this.bgColor,
    this.entryIndex,
    this.exitIndex,
  });

  final List<CandlestickDatum> candles;
  final Color bullColor;
  final Color bearColor;
  final Color gridColor;
  final Color bgColor;
  final int? entryIndex;
  final int? exitIndex;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawRect(Offset.zero & size, Paint()..color = bgColor);

    if (candles.isEmpty) return;

    double minY = double.infinity;
    double maxY = double.negativeInfinity;
    for (final c in candles) {
      minY = min(minY, c.low);
      maxY = max(maxY, c.high);
    }
    final pad = (maxY - minY) * 0.06 + 1e-6;
    minY -= pad;
    maxY += pad;

    for (var i = 1; i <= 4; i++) {
      final dy = size.height * i / 5;
      canvas.drawLine(
        Offset(0, dy),
        Offset(size.width, dy),
        Paint()
          ..color = gridColor
          ..strokeWidth = 1,
      );
    }

    final n = candles.length;
    final slot = size.width / n;
    final bodyW = max(2.0, slot * 0.55);

    double yPx(double price) {
      final t = (price - minY) / (maxY - minY);
      return size.height - t * size.height;
    }

    void paintMarker(int idx, Color color) {
      if (idx < 0 || idx >= n) return;
      final cx = idx * slot + slot / 2;
      final paint = Paint()
        ..color = color.withValues(alpha: 0.35)
        ..strokeWidth = 3;
      canvas.drawLine(Offset(cx, 0), Offset(cx, size.height), paint);
    }

    if (entryIndex != null) paintMarker(entryIndex!, const Color(0xFF38BDF8));
    if (exitIndex != null) paintMarker(exitIndex!, const Color(0xFFA855F7));

    for (var i = 0; i < n; i++) {
      final c = candles[i];
      final cx = i * slot + slot / 2;
      final bull = c.isBullish;
      final color = bull ? bullColor : bearColor;
      final yHigh = yPx(c.high);
      final yLow = yPx(c.low);
      final yOpen = yPx(c.open);
      final yClose = yPx(c.close);
      final top = min(yOpen, yClose);
      final bottom = max(yOpen, yClose);

      canvas.drawLine(
        Offset(cx, yHigh),
        Offset(cx, yLow),
        Paint()
          ..color = color
          ..strokeWidth = 1.2,
      );

      final rect = Rect.fromLTRB(cx - bodyW / 2, top, cx + bodyW / 2, bottom);
      canvas.drawRect(
        rect,
        Paint()
          ..color = color
          ..style = bull ? PaintingStyle.stroke : PaintingStyle.fill
          ..strokeWidth = 1.4,
      );
      if (bull) {
        canvas.drawRect(rect, Paint()..color = color.withValues(alpha: 0.25));
      }
    }
  }

  @override
  bool shouldRepaint(covariant _CandlestickPainter oldDelegate) {
    return oldDelegate.candles != candles ||
        oldDelegate.entryIndex != entryIndex ||
        oldDelegate.exitIndex != exitIndex;
  }
}

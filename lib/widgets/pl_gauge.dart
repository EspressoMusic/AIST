import 'package:flutter/material.dart';

class PlGauge extends StatelessWidget {
  const PlGauge({
    super.key,
    required this.profitLoss,
    required this.balanceBase,
  });

  final double profitLoss;
  final double balanceBase;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    const strongRange = 500.0;
    final direction = profitLoss == 0 ? 0.0 : (profitLoss > 0 ? 1.0 : -1.0);
    final magnitude = (profitLoss.abs() / strongRange).clamp(0.0, 1.0);
    final fillLevel = (0.5 + direction * magnitude * 0.42).clamp(0.08, 0.92);

    final gaugeColor = _gaugeColor(profitLoss);
    final sign = profitLoss >= 0 ? '+' : '-';
    final percent = balanceBase == 0 ? 0.0 : (profitLoss / balanceBase) * 100;

    return TweenAnimationBuilder<double>(
      tween: Tween<double>(begin: 0.5, end: fillLevel),
      duration: const Duration(milliseconds: 900),
      curve: Curves.easeOutQuart,
      builder: (context, value, _) {
        return SizedBox(
          width: 270,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 240,
                height: 240,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: gaugeColor.withValues(alpha: 0.22),
                      blurRadius: 34,
                      spreadRadius: 4,
                    ),
                  ],
                ),
                child: CustomPaint(
                  painter: _LiquidGaugePainter(
                    fillLevel: value,
                    liquidColor: gaugeColor,
                    emptyColor: const Color(0xFF07111F),
                    borderColor: gaugeColor.withValues(alpha: 0.82),
                    centerLineColor: scheme.onSurfaceVariant.withValues(
                      alpha: 0.34,
                    ),
                    wavePhase: magnitude * 2.4,
                  ),
                  child: Center(
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 14,
                        vertical: 8,
                      ),
                      decoration: BoxDecoration(
                        color: const Color(0xFF07111F).withValues(alpha: 0.38),
                        borderRadius: BorderRadius.circular(999),
                        border: Border.all(
                          color: Colors.white.withValues(alpha: 0.10),
                        ),
                      ),
                      child: Text(
                        '$sign\$${profitLoss.abs().toStringAsFixed(2)}',
                        style: TextStyle(
                          fontSize: 21,
                          fontWeight: FontWeight.w900,
                          color: Colors.white.withValues(alpha: 0.94),
                          letterSpacing: 0.2,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'רווח / הפסד כולל',
                style: TextStyle(
                  color: scheme.onSurfaceVariant,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                '${percent >= 0 ? '+' : ''}${percent.toStringAsFixed(2)}%',
                style: TextStyle(
                  color: gaugeColor,
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Color _gaugeColor(double pl) {
    if (pl < 0) return const Color(0xFFEF4444);
    return const Color(0xFF3B82F6);
  }
}

class _LiquidGaugePainter extends CustomPainter {
  const _LiquidGaugePainter({
    required this.fillLevel,
    required this.liquidColor,
    required this.emptyColor,
    required this.borderColor,
    required this.centerLineColor,
    required this.wavePhase,
  });

  final double fillLevel;
  final Color liquidColor;
  final Color emptyColor;
  final Color borderColor;
  final Color centerLineColor;
  final double wavePhase;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    final circlePath = Path()..addOval(rect.deflate(2));

    final bgPaint = Paint()
      ..shader = RadialGradient(
        center: const Alignment(-0.2, -0.45),
        radius: 1.0,
        colors: [
          emptyColor.withValues(alpha: 0.96),
          emptyColor,
          Colors.black.withValues(alpha: 0.62),
        ],
      ).createShader(rect);
    canvas.drawPath(circlePath, bgPaint);

    canvas.save();
    canvas.clipPath(circlePath);

    final waveTop = size.height * (1 - fillLevel);
    final amplitude = size.height * 0.028;
    final wave = Path()..moveTo(0, waveTop);
    for (double x = 0; x <= size.width; x += 4) {
      final y =
          waveTop +
          amplitude *
              (0.65 * (x / size.width) + 1) *
              _fastSin((x / size.width * 6.28318) + wavePhase);
      wave.lineTo(x, y);
    }
    wave
      ..lineTo(size.width, size.height)
      ..lineTo(0, size.height)
      ..close();

    final liquidPaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          liquidColor.withValues(alpha: 0.72),
          liquidColor.withValues(alpha: 0.98),
        ],
      ).createShader(rect);
    canvas.drawPath(wave, liquidPaint);

    final shine = Path()..moveTo(0, waveTop - amplitude * 0.3);
    for (double x = 0; x <= size.width; x += 4) {
      final y =
          waveTop -
          amplitude * 0.3 +
          amplitude *
              0.55 *
              _fastSin((x / size.width * 6.28318) + wavePhase + 0.9);
      shine.lineTo(x, y);
    }
    shine
      ..lineTo(size.width, waveTop + size.height * 0.08)
      ..lineTo(0, waveTop + size.height * 0.08)
      ..close();
    canvas.drawPath(
      shine,
      Paint()..color = Colors.white.withValues(alpha: 0.12),
    );

    final centerY = size.height / 2;
    final linePaint = Paint()
      ..color = centerLineColor
      ..strokeWidth = 1.2;
    canvas.drawLine(
      Offset(size.width * 0.18, centerY),
      Offset(size.width * 0.82, centerY),
      linePaint,
    );

    canvas.restore();

    final borderPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.2
      ..color = borderColor;
    canvas.drawOval(rect.deflate(2), borderPaint);
  }

  double _fastSin(double v) {
    // Small approximation is enough for a soft decorative wave.
    const pi = 3.141592653589793;
    v = v % (2 * pi);
    if (v > pi) v -= 2 * pi;
    return (16 * v * (pi - v.abs())) /
        (5 * pi * pi - 4 * v.abs() * (pi - v.abs()));
  }

  @override
  bool shouldRepaint(covariant _LiquidGaugePainter oldDelegate) {
    return oldDelegate.fillLevel != fillLevel ||
        oldDelegate.liquidColor != liquidColor ||
        oldDelegate.borderColor != borderColor ||
        oldDelegate.centerLineColor != centerLineColor ||
        oldDelegate.wavePhase != wavePhase;
  }
}

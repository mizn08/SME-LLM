import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

class KPICard extends StatelessWidget {
  const KPICard({
    super.key,
    required this.title,
    required this.value,
    this.subtitle,
    this.leading,
    this.trend,
  });

  final String title;
  final String value;
  final String? subtitle;
  final Widget? leading;
  final Widget? trend;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      padding: const EdgeInsets.all(20),
      decoration: AppTheme.cardDecoration(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              if (leading != null) ...[leading!, const SizedBox(width: 10)],
              Expanded(
                child: Text(
                  title.toUpperCase(),
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.8,
                    color: AppTheme.mutedForeground,
                  ),
                ),
              ),
              if (trend != null) trend!,
            ],
          ),
          const SizedBox(height: 10),
          Text(
            value,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textPrimary,
                ),
          ),
          if (subtitle != null)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                subtitle!,
                style: TextStyle(color: Colors.grey.shade500, fontSize: 12),
              ),
            ),
        ],
      ),
    );
  }
}

/// Animated donut-style health score
class HealthScoreGauge extends StatefulWidget {
  const HealthScoreGauge({
    super.key,
    required this.score,
    required this.label,
    this.letterGrade,
  });

  final int score;
  final String label;
  final String? letterGrade;

  @override
  State<HealthScoreGauge> createState() => _HealthScoreGaugeState();
}

class _HealthScoreGaugeState extends State<HealthScoreGauge> with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 1200));
    _anim = CurvedAnimation(parent: _ctrl, curve: Curves.easeOutExpo);
    _ctrl.forward();
  }

  @override
  void didUpdateWidget(HealthScoreGauge old) {
    super.didUpdateWidget(old);
    if (old.score != widget.score) _ctrl.forward(from: 0);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final Color scoreColor;
    if (widget.score >= 75) {
      scoreColor = AppTheme.accentGreen;
    } else if (widget.score >= 55) {
      scoreColor = AppTheme.gold;
    } else {
      scoreColor = Colors.red.shade400;
    }

    return AnimatedBuilder(
      animation: _anim,
      builder: (_, __) {
        return SizedBox(
          height: 160,
          width: 160,
          child: CustomPaint(
            painter: _GaugePainter(
              progress: _anim.value * (widget.score / 100.0),
              trackColor: Colors.grey.shade100,
              progressColor: scoreColor,
            ),
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    '${(_anim.value * widget.score).round()}',
                    style: TextStyle(
                      fontSize: 40,
                      fontWeight: FontWeight.w800,
                      color: AppTheme.textPrimary,
                      height: 1,
                    ),
                  ),
                  if (widget.letterGrade != null)
                    Text(
                      'Grade ${widget.letterGrade}',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                        color: scoreColor,
                      ),
                    ),
                  const SizedBox(height: 4),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                    decoration: BoxDecoration(
                      color: scoreColor.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      widget.label,
                      style: TextStyle(
                        color: scoreColor,
                        fontWeight: FontWeight.w700,
                        fontSize: 12,
                        letterSpacing: 1,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _GaugePainter extends CustomPainter {
  _GaugePainter({required this.progress, required this.trackColor, required this.progressColor});

  final double progress;
  final Color trackColor;
  final Color progressColor;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2 - 10;
    const startAngle = -math.pi * 0.75;
    const sweepAngle = math.pi * 1.5;

    // Track
    final trackPaint = Paint()
      ..color = trackColor
      ..strokeWidth = 12
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      sweepAngle,
      false,
      trackPaint,
    );

    // Progress
    final progressPaint = Paint()
      ..shader = SweepGradient(
        startAngle: startAngle,
        endAngle: startAngle + sweepAngle,
        colors: [progressColor.withOpacity(0.6), progressColor],
      ).createShader(Rect.fromCircle(center: center, radius: radius))
      ..strokeWidth = 12
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      sweepAngle * progress,
      false,
      progressPaint,
    );

    // Dot at end
    if (progress > 0.01) {
      final angle = startAngle + sweepAngle * progress;
      final dotCenter = Offset(
        center.dx + radius * math.cos(angle),
        center.dy + radius * math.sin(angle),
      );
      canvas.drawCircle(dotCenter, 7, Paint()..color = progressColor);
      canvas.drawCircle(dotCenter, 4, Paint()..color = Colors.white);
    }
  }

  @override
  bool shouldRepaint(_GaugePainter old) => old.progress != progress;
}

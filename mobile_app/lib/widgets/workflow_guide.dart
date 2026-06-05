import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Shneiderman "overview first" — 4-step journey visible on Home.
class WorkflowGuide extends StatelessWidget {
  const WorkflowGuide({
    super.key,
    required this.currentStep,
    this.onStepTap,
  });

  /// 0=Understand 1=Plan 2=Ask 3=Fund
  final int currentStep;
  final void Function(int step)? onStepTap;

  static const _steps = [
    _StepData('Understand', 'See your pulse', Icons.favorite_outline_rounded, AppTheme.midnight),
    _StepData('Design', 'Brief & quote', Icons.engineering_outlined, AppTheme.ember),
    _StepData('BNPL', 'Advisor chat', Icons.psychology_outlined, AppTheme.midnightLight),
    _StepData('Fund', 'Grants & loans', Icons.assured_workload_outlined, AppTheme.emberDark),
  ];

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Your journey',
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppTheme.textSecondary),
          ),
          const SizedBox(height: 4),
          Text(
            'Follow these steps — tap any step to jump there.',
            style: TextStyle(fontSize: 11, color: AppTheme.mutedForeground.withOpacity(0.9)),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              for (var i = 0; i < _steps.length; i++) ...[
                if (i > 0)
                  Expanded(
                    child: Container(
                      height: 2,
                      margin: const EdgeInsets.only(bottom: 28),
                      decoration: BoxDecoration(
                        color: i <= currentStep ? AppTheme.midnightLight : AppTheme.borderColor,
                        borderRadius: BorderRadius.circular(1),
                      ),
                    ),
                  ),
                Expanded(
                  child: _StepChip(
                    data: _steps[i],
                    index: i,
                    active: i == currentStep,
                    done: i < currentStep,
                    onTap: onStepTap != null ? () => onStepTap!(i) : null,
                  ),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }
}

class _StepData {
  const _StepData(this.label, this.hint, this.icon, this.color);
  final String label;
  final String hint;
  final IconData icon;
  final Color color;
}

class _StepChip extends StatelessWidget {
  const _StepChip({
    required this.data,
    required this.index,
    required this.active,
    required this.done,
    this.onTap,
  });

  final _StepData data;
  final int index;
  final bool active;
  final bool done;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final bg = active
        ? AppTheme.accentWash
        : done
            ? AppTheme.successBg
            : AppTheme.surfaceCard;
    final border = active ? data.color.withOpacity(0.55) : AppTheme.borderColor;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Column(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: bg,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: border, width: active ? 2 : 1),
              ),
              child: Icon(
                done ? Icons.check_rounded : data.icon,
                color: done ? AppTheme.successFg : data.color,
                size: 22,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              data.label,
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 9,
                height: 1.15,
                fontWeight: active ? FontWeight.w700 : FontWeight.w500,
                color: active ? AppTheme.textPrimary : AppTheme.mutedForeground,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Quick actions on Home — recognition over recall (Nielsen #6).
class QuickActionGrid extends StatelessWidget {
  const QuickActionGrid({
    super.key,
    required this.onSimulate,
    required this.onAskAi,
    required this.onGrants,
    required this.onUpload,
  });

  final VoidCallback onSimulate;
  final VoidCallback onAskAi;
  final VoidCallback onGrants;
  final VoidCallback onUpload;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Quick actions',
            style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: AppTheme.textPrimary),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: _ActionTile(
                  label: 'BNPL Chat',
                  icon: Icons.psychology_rounded,
                  gradient: AppTheme.askAiGradient,
                  onTap: onAskAi,
                  emphasized: true,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _ActionTile(
                  label: 'Finance',
                  icon: Icons.calculate_rounded,
                  color: AppTheme.surfaceCard,
                  iconColor: AppTheme.brandBlue,
                  onTap: onSimulate,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: _ActionTile(
                  label: 'Find funding',
                  icon: Icons.assured_workload_rounded,
                  color: AppTheme.surfaceCard,
                  iconColor: AppTheme.goldAccent,
                  onTap: onGrants,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _ActionTile(
                  label: 'Upload data',
                  icon: Icons.upload_file_rounded,
                  color: AppTheme.surfaceCard,
                  iconColor: AppTheme.skyBlue,
                  onTap: onUpload,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ActionTile extends StatelessWidget {
  const _ActionTile({
    required this.label,
    required this.icon,
    required this.onTap,
    this.color,
    this.iconColor,
    this.gradient,
    this.emphasized = false,
  });

  final String label;
  final IconData icon;
  final VoidCallback onTap;
  final Color? color;
  final Color? iconColor;
  final Gradient? gradient;
  final bool emphasized;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          height: emphasized ? 84 : 68,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            gradient: gradient,
            color: gradient == null ? color : null,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppTheme.borderColor),
            boxShadow: emphasized ? AppTheme.cardShadow : null,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Icon(icon, color: emphasized ? Colors.white : iconColor, size: 24),
              Text(
                label,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 12,
                  height: 1.15,
                  color: emphasized ? Colors.white : AppTheme.textPrimary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

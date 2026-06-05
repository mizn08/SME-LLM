import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Renders chat text with **bold** markdown segments.
class FormattedChatText extends StatelessWidget {
  const FormattedChatText({
    super.key,
    required this.text,
    this.style,
    this.boldStyle,
  });

  final String text;
  final TextStyle? style;
  final TextStyle? boldStyle;

  static final RegExp _boldPattern = RegExp(r'\*\*(.+?)\*\*');

  @override
  Widget build(BuildContext context) {
    final base = style ?? const TextStyle(fontSize: 14, height: 1.45);
    final bold = boldStyle ??
        base.copyWith(fontWeight: FontWeight.w700, color: AppTheme.textPrimary);

    final spans = <InlineSpan>[];
    var start = 0;
    for (final match in _boldPattern.allMatches(text)) {
      if (match.start > start) {
        spans.add(TextSpan(text: text.substring(start, match.start), style: base));
      }
      spans.add(TextSpan(text: match.group(1), style: bold));
      start = match.end;
    }
    if (start < text.length) {
      spans.add(TextSpan(text: text.substring(start), style: base));
    }
    if (spans.isEmpty) {
      return Text(text, style: base);
    }
    return Text.rich(TextSpan(children: spans));
  }
}

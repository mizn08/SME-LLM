import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/chat_message.dart';
import '../models/prediction.dart';
import '../l10n/app_strings.dart';
import '../providers/recommendation_provider.dart';
import '../providers/advisor_nav_provider.dart';
import '../providers/session_provider.dart';
import '../providers/settings_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/lead_score_meter.dart';
import '../widgets/recommendation_result.dart';
import '../widgets/active_profile_badge.dart';
import '../widgets/formatted_chat_text.dart';
import '../widgets/sales_engineer_tab.dart';
import 'guided_advisory_screen.dart';

class AiAdvisorScreen extends StatefulWidget {
  const AiAdvisorScreen({super.key});

  @override
  State<AiAdvisorScreen> createState() => _AiAdvisorScreenState();
}

class _AiAdvisorScreenState extends State<AiAdvisorScreen> with SingleTickerProviderStateMixin {
  late final TabController _tabs;
  final _input = TextEditingController();
  final _api = ApiService();
  final List<ChatTurn> _history = [];
  bool _chatBusy = false;
  String? _persona;
  AgentAdvice? _agentAdvice;
  bool _agentBusy = false;
  String? _err;
  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 5, vsync: this);
    _history.add(
      ChatTurn(
        role: 'assistant',
        text:
            'Hi — I\'m your SME LLM BNPL Advisor. Ask about cash flow, grants, BNPL instalments, or financing after a quote. '
            'Answers use your live SME profile and sync with Design & Finance.',
      ),
    );
    WidgetsBinding.instance.addPostFrameCallback((_) => _applyPendingSubTab());
  }

  void _applyPendingSubTab() {
    if (!mounted) return;
    final pending = context.read<AdvisorNavProvider>().consumePending();
    if (pending != null && pending >= 0 && pending < _tabs.length) {
      _tabs.animateTo(pending);
    }
  }

  void _syncRagFromSalesEngineer(String brief, String ragAnswer, List<ChatSource> sources) {
    setState(() {
      _history.add(ChatTurn(role: 'user', text: 'SME purchase brief: $brief'));
      _history.add(ChatTurn(role: 'assistant', text: ragAnswer, sources: sources));
    });
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Quote finished — RAG advice synced to chat')),
    );
  }

  @override
  void dispose() {
    _tabs.dispose();
    _input.dispose();
    super.dispose();
  }

  Future<void> _sendChat() async {
    final text = _input.text.trim();
    if (text.isEmpty || _chatBusy) return;
    setState(() {
      _chatBusy = true;
      _err = null;
      _history.add(ChatTurn(role: 'user', text: text));
      _input.clear();
    });
    final sid = context.read<SessionProvider>().smeId;
    final lang = context.read<SettingsProvider>().locale.languageCode;
    final rec = context.read<RecommendationProvider>();
    final purchaseAmt = rec.lastPurchaseAmount;
    final purchaseCat = rec.lastPurchaseCategory;
    final mem = _history
        .where((t) => t.role == 'user' || t.role == 'assistant')
        .map((t) => {'role': t.role, 'text': t.text})
        .toList();
    var assistantIdx = -1;
    setState(() {
      _history.add(ChatTurn(role: 'assistant', text: ''));
      assistantIdx = _history.length - 1;
    });
    try {
      var streamed = false;
      try {
        await for (final chunk in _api.chatStream(
          smeId: sid,
          message: text,
          persona: _persona,
          language: lang,
          purchaseAmount: purchaseAmt,
          purchaseCategory: purchaseCat,
        )) {
          streamed = true;
          if (!mounted || assistantIdx < 0) return;
          setState(() {
            _history[assistantIdx] = ChatTurn(
              role: 'assistant',
              text: _history[assistantIdx].text + chunk,
            );
          });
        }
      } catch (_) {
        streamed = false;
      }
      if (!streamed || _history[assistantIdx].text.isEmpty) {
        final res = await _api.chat(
          smeId: sid,
          message: text,
          persona: _persona,
          language: lang,
          history: mem,
          purchaseAmount: purchaseAmt,
          purchaseCategory: purchaseCat,
        );
        if (!mounted) return;
        setState(() {
          _history[assistantIdx] = ChatTurn(
            role: 'assistant',
            text: res.answer,
            sources: res.sources,
          );
        });
      }
    } catch (e) {
      if (assistantIdx >= 0 && _history[assistantIdx].text.isEmpty) {
        _history.removeAt(assistantIdx);
      }
      if (!mounted) return;
      setState(() => _err = ApiService.friendlyError(e));
    } finally {
      if (mounted) setState(() => _chatBusy = false);
    }
  }

  Future<void> _runAgents() async {
    final rec = context.read<RecommendationProvider>();
    final amt = rec.lastPurchaseAmount ?? 50000;
    final cat = rec.lastPurchaseCategory ?? 'equipment';
    setState(() {
      _agentBusy = true;
      _err = null;
    });
    try {
      final sid = context.read<SessionProvider>().smeId;
      final advice = await _api.agentAdvise(
        smeId: sid,
        purchaseAmount: amt,
        purchaseCategory: cat,
        goal: 'best financing for SME',
      );
      if (!mounted) return;
      setState(() => _agentAdvice = advice);
    } catch (e) {
      if (!mounted) return;
      setState(() => _err = ApiService.friendlyError(e));
    } finally {
      if (mounted) setState(() => _agentBusy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = AppStrings(context.watch<SettingsProvider>().locale);
    return Column(
      children: [
        Material(
          color: AppTheme.surfaceCard,
          child: TabBar(
            controller: _tabs,
            labelColor: AppTheme.midnight,
            unselectedLabelColor: AppTheme.mutedForeground,
            indicatorColor: AppTheme.ember,
            isScrollable: true,
            tabs: [
              Tab(text: s.tabRagChat),
              Tab(text: s.tabAgents),
              Tab(text: s.tabMlInsight),
              Tab(text: s.tabGuided),
              Tab(text: s.tabSalesEngineer),
            ],
          ),
        ),
        const ActiveProfileBadge(),
        if (_err != null)
          Padding(
            padding: const EdgeInsets.all(8),
            child: Text(_err!, style: const TextStyle(color: Colors.red, fontSize: 12)),
          ),
        Expanded(
          child: TabBarView(
            controller: _tabs,
            children: [
              _chatTab(),
              _agentsTab(),
              _mlTab(),
              const GuidedAdvisoryScreen(),
              SalesEngineerTab(
                api: _api,
                onRagSynced: _syncRagFromSalesEngineer,
                onOpenRagChat: () => _tabs.animateTo(0),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _personaChip(String label, String id) {
    final selected = _persona == id;
    return FilterChip(
      label: Text(label, style: const TextStyle(fontSize: 12)),
      selected: selected,
      onSelected: (v) => setState(() => _persona = v ? id : null),
      selectedColor: AppTheme.surfaceElevated,
      checkmarkColor: AppTheme.midnight,
    );
  }

  Widget _chatTab() {
    final rec = context.watch<RecommendationProvider>();
    final amt = rec.lastPurchaseAmount ?? 50000;
    final cat = rec.lastPurchaseCategory ?? 'equipment';
    return Column(
      children: [
        Container(
          width: double.infinity,
          margin: const EdgeInsets.fromLTRB(12, 8, 12, 0),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: AppTheme.surfaceElevated,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppTheme.borderGlow),
          ),
          child: Text(
            'Synced with Financing Simulator: RM ${amt.toStringAsFixed(0)} · $cat',
            style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary, height: 1.3),
          ),
        ),
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(12),
            itemCount: _history.length,
            itemBuilder: (_, i) {
              final t = _history[i];
              final isUser = t.role == 'user';
              return Align(
                alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                child: Container(
                  margin: const EdgeInsets.only(bottom: 10),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * 0.85),
                  decoration: BoxDecoration(
                    color: isUser ? const Color(0xFFE8EDF5) : AppTheme.surfaceCard,
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(
                      color: isUser ? AppTheme.midnight.withOpacity(0.35) : AppTheme.borderColor,
                    ),
                    boxShadow: isUser ? null : AppTheme.cardShadow,
                  ),
                  child: isUser
                      ? Text(t.text, style: const TextStyle(fontSize: 14, height: 1.45))
                      : FormattedChatText(text: t.text),
                ),
              );
            },
          ),
        ),
        if (_chatBusy) const LinearProgressIndicator(minHeight: 2, color: AppTheme.ember),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: Wrap(
            spacing: 8,
            children: [
              _personaChip('Puan Sarah', 'banker'),
              _personaChip('Uncle Ah Kow', 'towkay'),
              _personaChip('Dr Aisha', 'mdec'),
            ],
          ),
        ),
        SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 4, 12, 12),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _input,
                    decoration: InputDecoration(
                      hintText: 'e.g. Which grant fits digital purchases?',
                      filled: true,
                      fillColor: Colors.white,
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                    ),
                    onSubmitted: (_) => _sendChat(),
                  ),
                ),
                const SizedBox(width: 4),
                IconButton.filled(
                  onPressed: _chatBusy ? null : _sendChat,
                  icon: const Icon(Icons.send_rounded),
                  style: IconButton.styleFrom(backgroundColor: AppTheme.midnight),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _agentsTab() {
    final rec = context.watch<RecommendationProvider>();
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(
          'LangChain multi-agent: Grant, BNPL, and Cash specialists coordinate on your scenario.',
          style: TextStyle(color: Colors.grey.shade600, fontSize: 13, height: 1.4),
        ),
        const SizedBox(height: 12),
        Text(
          'Using RM ${(rec.lastPurchaseAmount ?? 5000).toStringAsFixed(0)} · '
          '${rec.lastPurchaseCategory ?? 'equipment'}',
          style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
        ),
        const SizedBox(height: 12),
        FilledButton.icon(
          onPressed: _agentBusy ? null : _runAgents,
          icon: _agentBusy
              ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
              : const Icon(Icons.hub_rounded),
          label: const Text('Run multi-agent advise'),
          style: FilledButton.styleFrom(backgroundColor: AppTheme.teal, padding: const EdgeInsets.symmetric(vertical: 14)),
        ),
        if (_agentAdvice != null) ...[
          const SizedBox(height: 20),
          _agentCard('Lead: ${_agentAdvice!.leadAgent}', _agentAdvice!.summary),
          ..._agentAdvice!.agents.map(
            (a) => _agentCard(a.name.toUpperCase(), a.insight),
          ),
          if (_agentAdvice!.ragSnippet != null)
            _agentCard('RAG context', _agentAdvice!.ragSnippet!),
        ],
      ],
    );
  }

  Widget _agentCard(String title, String body) {
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      elevation: 0,
      color: AppTheme.teal.withOpacity(0.06),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
            const SizedBox(height: 6),
            Text(body, style: TextStyle(color: Colors.grey.shade800, height: 1.45, fontSize: 13)),
          ],
        ),
      ),
    );
  }

  Widget _mlTab() {
    return Consumer<RecommendationProvider>(
      builder: (context, rec, _) {
        final r = rec.lastResult;
        if (r == null) {
          return Center(
            child: Padding(
              padding: const EdgeInsets.all(32),
              child: Text(
                'Run Financing Simulator first for ML + SHAP insight.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey.shade500),
              ),
            ),
          );
        }
        return ListView(
          padding: const EdgeInsets.all(8),
          children: [
            RecommendationResultCard(result: r),
            if (r.leadScores.isNotEmpty)
              PremiumCard(
                margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                child: Column(
                  children: [
                    for (final s in r.leadScores)
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 6),
                        child: LeadScoreMeter(item: s),
                      ),
                  ],
                ),
              ),
            ShapFactorsList(items: r.shapValues),
            _financialBreakdown(context, r),
            const SizedBox(height: 24),
          ],
        );
      },
    );
  }

  Widget _financialBreakdown(BuildContext context, PredictionResult r) {
    return PremiumCard(
      margin: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppTheme.teal.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.wallet_rounded, color: AppTheme.teal, size: 20),
              ),
              const SizedBox(width: 10),
              Text(
                'Financial Breakdown',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
              ),
            ],
          ),
          const SizedBox(height: 16),
          _row('Simulated decision', r.recommendationType),
          _row('Product', r.productName),
          _row('Cash preserved (est.)', 'RM ${r.cashPreservedRm.toStringAsFixed(2)}'),
          _row('Additional cost (est.)', 'RM ${r.additionalCostRm.toStringAsFixed(2)}'),
          _row('Model financing probability', '${(r.mlProbability * 100).toStringAsFixed(1)}%'),
        ],
      ),
    );
  }

  Widget _row(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 7),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 160,
              child: Text(k, style: TextStyle(color: Colors.grey.shade500, fontSize: 13)),
            ),
            Expanded(
              child: Text(v, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
            ),
          ],
        ),
      );
}

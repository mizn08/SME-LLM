import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';

import '../models/application_tracker.dart';
import '../models/benchmark.dart';
import '../models/bnpl_repayment.dart';
import '../models/chat_message.dart';
import '../models/digest.dart';
import '../models/grant_checklist.dart';
import '../models/guided_advisory.dart';
import '../models/lead_score.dart';
import '../models/lender.dart';
import '../models/nudge.dart';
import '../models/spending_category.dart';
import 'cache_service.dart';
import '../data/malaysia_bnpl_plans.dart';
import '../models/dashboard.dart';
import '../models/gov_aid.dart';
import '../models/prediction.dart';
import '../utils/constants.dart';

class ApiService {
  ApiService()
      : _dio = Dio(
          BaseOptions(
            baseUrl: resolveApiBase(),
            connectTimeout: const Duration(seconds: 90),
            receiveTimeout: const Duration(seconds: 90),
            sendTimeout: const Duration(seconds: 60),
          ),
        );

  final Dio _dio;

  static bool isNotFound(DioException e) => e.response?.statusCode == 404;

  static String friendlyError(Object e) {
    if (e is DioException && isNotFound(e)) {
      return 'This feature needs API v5. Use a local backend (run_local.ps1) '
          'or redeploy Render with the latest code.';
    }
    if (e is DioException) return e.message ?? e.toString();
    return e.toString();
  }

  Future<DashboardData> fetchDashboard(int smeId, {bool useCacheOnFail = true}) async {
    try {
      final res = await _dio.get('/sme/$smeId/dashboard');
      final map = res.data as Map<String, dynamic>;
      await CacheService.saveDashboard(smeId, map);
      return DashboardData.fromJson(map);
    } catch (_) {
      if (!useCacheOnFail) rethrow;
      final cached = await CacheService.loadDashboard(smeId);
      if (cached != null) return DashboardData.fromJson(cached);
      rethrow;
    }
  }

  Future<Map<String, dynamic>> compareFinancing({
    required int smeId,
    required double purchaseAmount,
    required String purchaseCategory,
    bool includeSst = false,
    bool islamicOnly = false,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/compare',
      data: {
        'sme_id': smeId,
        'purchase_amount': purchaseAmount,
        'purchase_category': purchaseCategory,
        'include_sst': includeSst,
        'islamic_only': islamicOnly,
      },
    );
    return res.data ?? {};
  }

  Future<Map<String, dynamic>> fetchSectorPlaybooks() async {
    final res = await _dio.get<Map<String, dynamic>>('/sector-playbooks');
    return res.data ?? {};
  }

  Future<PredictionResult> predict({
    required int smeId,
    required double purchaseAmount,
    required String purchaseCategory,
    String? selectedBnplPlan,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/predict',
      data: {
        'sme_id': smeId,
        'purchase_amount': purchaseAmount,
        'purchase_category': purchaseCategory,
        'selected_bnpl_plan': selectedBnplPlan,
      },
    );
    final data = res.data;
    if (data == null) {
      throw DioException(
        requestOptions: res.requestOptions,
        message: 'Empty response from /predict',
      );
    }
    return PredictionResult.fromJson(data);
  }

  Future<List<GovAid>> fetchGovAid() async {
    final res = await _dio.get<List<dynamic>>('/gov-aid');
    return (res.data ?? []).map((e) => GovAid.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<PredictionHistoryItem>> fetchHistory(int smeId) async {
    final res = await _dio.get<List<dynamic>>('/sme/$smeId/predictions');
    return (res.data ?? []).map((e) => PredictionHistoryItem.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Map<String, dynamic>> fetchPredictionDetail(int id) async {
    final res = await _dio.get<Map<String, dynamic>>('/predictions/$id');
    return res.data ?? {};
  }

  Future<Map<String, dynamic>> fetchModelMetrics() async {
    final res = await _dio.get<Map<String, dynamic>>('/model-metrics');
    return res.data ?? {};
  }

  Future<ChatResponse> chat({
    required int smeId,
    required String message,
    String? persona,
    String? language,
    List<Map<String, String>>? history,
  }) async {
    final data = {
      'sme_id': smeId,
      'message': message,
      if (persona != null) 'persona': persona,
      if (language != null) 'language': language,
    };
    final res = history != null && history.isNotEmpty
        ? await _dio.post<Map<String, dynamic>>(
            '/chat/memory',
            data: {
              ...data,
              'history': history
                  .map((h) => {'role': h['role'], 'text': h['text']})
                  .toList(),
            },
          )
        : await _dio.post<Map<String, dynamic>>('/chat', data: data);
    return ChatResponse.fromJson(res.data ?? {});
  }

  Stream<String> chatStream({
    required int smeId,
    required String message,
    String? persona,
    String? language,
  }) async* {
    final Response<ResponseBody> res;
    try {
      res = await _dio.get<ResponseBody>(
        '/chat/stream',
        queryParameters: {
          'sme_id': smeId,
          'message': message,
          if (persona != null) 'persona': persona,
          if (language != null) 'language': language,
        },
        options: Options(responseType: ResponseType.stream),
      );
    } on DioException catch (e) {
      if (isNotFound(e)) return;
      rethrow;
    }
    final stream = res.data?.stream;
    if (stream == null) return;
    var buffer = '';
    await for (final chunk in stream) {
      buffer += String.fromCharCodes(chunk);
      while (buffer.contains('\n\n')) {
        final idx = buffer.indexOf('\n\n');
        final block = buffer.substring(0, idx);
        buffer = buffer.substring(idx + 2);
        for (final line in block.split('\n')) {
          if (!line.startsWith('data: ')) continue;
          try {
            final obj = jsonDecode(line.substring(6).trim()) as Map<String, dynamic>;
            if (obj['type'] == 'token') {
              final t = obj['text'] as String? ?? '';
              if (t.isNotEmpty) yield t;
            }
          } catch (_) {}
        }
      }
    }
  }

  Future<NudgeResponse> fetchNudges(int smeId) async {
    try {
      final res = await _dio.get<Map<String, dynamic>>('/sme/$smeId/nudges');
      return NudgeResponse.fromJson(res.data ?? {});
    } on DioException catch (e) {
      if (isNotFound(e)) return _nudgesFromDashboardAlerts(smeId);
      rethrow;
    }
  }

  Future<NudgeResponse> _nudgesFromDashboardAlerts(int smeId) async {
    try {
      final dash = await fetchDashboard(smeId, useCacheOnFail: true);
      final items = dash.alerts.map((alert) {
        final critical = alert.toLowerCase().contains('critical');
        return NudgeItem(
          severity: critical ? 'critical' : 'warning',
          title: critical ? 'Critical alert' : 'Advisory',
          body: alert,
        );
      }).toList();
      return NudgeResponse(smeId: smeId, nudges: items);
    } catch (_) {
      return NudgeResponse(smeId: smeId, nudges: []);
    }
  }

  Future<Map<String, dynamic>> registerPushDevice({required int smeId, required String token}) async {
    try {
      final res = await _dio.post<Map<String, dynamic>>('/notifications/register', data: {
        'sme_id': smeId,
        'fcm_token': token,
        'platform': 'fcm',
      });
      return res.data ?? {};
    } on DioException catch (e) {
      if (isNotFound(e)) return {'status': 'skipped', 'fcm_configured': false, 'api_v5_required': true};
      rethrow;
    }
  }

  Future<Map<String, dynamic>> fetchNotificationStatus() async {
    try {
      final res = await _dio.get<Map<String, dynamic>>('/notifications/status');
      return res.data ?? {};
    } on DioException catch (e) {
      if (isNotFound(e)) return {'fcm_configured': false, 'api_v5_required': true};
      rethrow;
    }
  }

  Future<Map<String, dynamic>> sendTestPush({
    required int smeId,
    String title = 'SME Advisor',
    String body = 'Test push — your alerts are working.',
  }) async {
    try {
      final res = await _dio.post<Map<String, dynamic>>('/notifications/test', data: {
        'sme_id': smeId,
        'title': title,
        'body': body,
      });
      return res.data ?? {};
    } on DioException catch (e) {
      if (isNotFound(e)) return {'ok': false, 'error': 'api_v5_required', 'hint': friendlyError(e)};
      rethrow;
    }
  }

  Future<Map<String, dynamic>> sendNudgesPush(int smeId) async {
    try {
      final res = await _dio.post<Map<String, dynamic>>('/notifications/send', queryParameters: {
        'sme_id': smeId,
      });
      return res.data ?? {};
    } on DioException catch (e) {
      if (isNotFound(e)) return {'ok': false, 'error': 'api_v5_required', 'hint': friendlyError(e)};
      rethrow;
    }
  }

  Future<LeadScoreResponse> fetchLeadScores(int smeId) async {
    final res = await _dio.get<Map<String, dynamic>>('/sme/$smeId/lead-scores');
    return LeadScoreResponse.fromJson(res.data ?? {});
  }

  Future<String> generatePitch({
    required int smeId,
    String lang = 'en',
    String tone = 'formal',
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/sme/$smeId/pitch',
      data: {'lang': lang, 'tone': tone},
    );
    return res.data?['letter'] as String? ?? '';
  }

  Future<BenchmarkResponse> fetchBenchmark(int smeId) async {
    final res = await _dio.get<Map<String, dynamic>>('/sme/$smeId/benchmark');
    return BenchmarkResponse.fromJson(res.data ?? {});
  }

  Future<DigestResponse> fetchDigest(int smeId) async {
    final res = await _dio.get<Map<String, dynamic>>('/sme/$smeId/digest');
    return DigestResponse.fromJson(res.data ?? {});
  }

  Future<SpendingCategoryResponse> fetchSpendingCategories(int smeId) async {
    final res = await _dio.get<Map<String, dynamic>>('/sme/$smeId/spending-categories');
    return SpendingCategoryResponse.fromJson(res.data ?? {});
  }

  Future<LenderDirectoryResponse> fetchLenders({bool islamicOnly = false}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/lenders',
      queryParameters: {'islamic_only': islamicOnly},
    );
    return LenderDirectoryResponse.fromJson(res.data ?? {});
  }

  Future<List<LenderItem>> fetchMatchedLenders(int smeId, {bool islamicOnly = false}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/sme/$smeId/lenders/matched',
      queryParameters: {'islamic_only': islamicOnly},
    );
    return ((res.data?['matched'] as List<dynamic>? ?? [])
        .map((e) => LenderItem.fromJson(e as Map<String, dynamic>))
        .toList());
  }

  Future<GrantChecklistResponse> fetchGrantChecklist(int grantId) async {
    final res = await _dio.get<Map<String, dynamic>>('/grants/$grantId/checklist');
    return GrantChecklistResponse.fromJson(res.data ?? {});
  }

  Future<ApplicationTrackerResponse> fetchApplications(int smeId) async {
    final res = await _dio.get<Map<String, dynamic>>('/sme/$smeId/applications');
    return ApplicationTrackerResponse.fromJson(res.data ?? {});
  }

  Future<ApplicationTrackerItem> createApplication({
    required int smeId,
    required String productName,
    required String productType,
    String? notes,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/applications',
      data: {
        'sme_id': smeId,
        'product_name': productName,
        'product_type': productType,
        if (notes != null) 'notes': notes,
      },
    );
    return ApplicationTrackerItem.fromJson(res.data ?? {});
  }

  Future<ApplicationTrackerItem> updateApplication({
    required int id,
    String? status,
    String? notes,
  }) async {
    final res = await _dio.patch<Map<String, dynamic>>(
      '/applications/$id',
      data: {
        if (status != null) 'status': status,
        if (notes != null) 'notes': notes,
      },
    );
    return ApplicationTrackerItem.fromJson(res.data ?? {});
  }

  Future<List<Map<String, dynamic>>> fetchMarketplace({bool bnplOnly = false}) async {
    try {
      final res = await _dio.get<Map<String, dynamic>>(
        '/marketplace/providers',
        queryParameters: bnplOnly ? <String, dynamic>{'bnpl_only': true} : null,
      );
      final list = (res.data?['providers'] as List<dynamic>? ?? [])
          .map((e) => e as Map<String, dynamic>)
          .toList();
      if (list.length >= 5) return list;
    } on DioException catch (_) {}
    return MalaysiaBnplPlans.marketplaceProviders(bnplOnly: bnplOnly);
  }

  Future<List<Map<String, String?>>> fetchBnplPlanChoices() async {
    try {
      final res = await _dio.get<Map<String, dynamic>>('/bnpl/plan-choices');
      final choices = res.data?['choices'] as List<dynamic>? ?? [];
      final mapped = choices
          .map(
            (c) => {
              'label': c['label'] as String? ?? '',
              'value': c['value'] as String?,
            },
          )
          .toList();
      if (mapped.length >= 5) return mapped;
    } on DioException catch (_) {}
    return MalaysiaBnplPlans.planChoices;
  }

  Future<BnplRepaymentResponse> simulateBnplRepayment({
    required double amountRm,
    double annualRatePct = 12,
    int tenureMonths = 12,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/bnpl/repayment',
      data: {
        'amount_rm': amountRm,
        'annual_rate_pct': annualRatePct,
        'tenure_months': tenureMonths,
      },
    );
    return BnplRepaymentResponse.fromJson(res.data ?? {});
  }

  Future<GuidedAdvisoryResponse> guidedAdvisory({
    required int smeId,
    required String businessType,
    required String goal,
    required double amountRm,
    required int timelineMonths,
    required String mainConstraint,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/guided-advisory',
      data: {
        'sme_id': smeId,
        'business_type': businessType,
        'goal': goal,
        'amount_rm': amountRm,
        'timeline_months': timelineMonths,
        'main_constraint': mainConstraint,
      },
    );
    return GuidedAdvisoryResponse.fromJson(res.data ?? {});
  }

  Future<Map<String, dynamic>> fetchFinancingTimeline(int smeId) async {
    final res = await _dio.get<Map<String, dynamic>>('/sme/$smeId/financing-timeline');
    return res.data ?? {};
  }

  Future<Map<String, dynamic>> onboardProfile({
    int smeId = 1,
    required String sector,
    required double revenueRm,
    required int employeeCount,
    bool sstRegistered = false,
    double cashReserveMonths = 2,
    bool bumiputera = false,
    bool techFocus = false,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/profile/onboard',
      data: {
        'sme_id': smeId,
        'sector': sector,
        'revenue_rm': revenueRm,
        'employee_count': employeeCount,
        'sst_registered': sstRegistered,
        'cash_reserve_months': cashReserveMonths,
        'bumiputera': bumiputera,
        'tech_focus': techFocus,
      },
    );
    return res.data ?? {};
  }

  Future<Map<String, dynamic>> grantEligibility({
    int? smeId,
    bool bumiputera = false,
    double revenueRm = 0,
    String sector = '',
    bool ssmRegistered = true,
    bool techFocus = false,
    bool exportIntent = false,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/grants/eligibility',
      data: {
        if (smeId != null) 'sme_id': smeId,
        'bumiputera': bumiputera,
        'revenue_rm': revenueRm,
        'sector': sector,
        'ssm_registered': ssmRegistered,
        'tech_focus': techFocus,
        'export_intent': exportIntent,
      },
    );
    return res.data ?? {};
  }

  Future<Map<String, dynamic>> fetchReport(int smeId) async {
    final res = await _dio.get<Map<String, dynamic>>('/sme/$smeId/report');
    return res.data ?? {};
  }

  Future<Map<String, dynamic>> fetchInsights(int smeId) async {
    final res = await _dio.get<Map<String, dynamic>>('/sme/$smeId/insights');
    return res.data ?? {};
  }

  Future<Map<String, dynamic>> fetchBanditStats() async {
    final res = await _dio.get<Map<String, dynamic>>('/bandit/stats');
    return res.data ?? {};
  }

  Future<void> banditFeedback({
    required int smeId,
    required String arm,
    required bool accepted,
    int? predictionId,
  }) async {
    await _dio.post('/bandit/feedback', data: {
      'sme_id': smeId,
      'arm': arm,
      'accepted': accepted,
      'prediction_id': predictionId,
    });
  }

  Future<Map<String, dynamic>> uploadInvoice({
    required int smeId,
    required List<int> bytes,
    required String fileName,
  }) async {
    final form = FormData.fromMap({
      'sme_id': smeId,
      'file': MultipartFile.fromBytes(bytes, filename: fileName),
    });
    final res = await _dio.post<Map<String, dynamic>>('/upload-invoice', data: form);
    return res.data ?? {};
  }

  Future<AgentAdvice> agentAdvise({
    required int smeId,
    required double purchaseAmount,
    required String purchaseCategory,
    String? goal,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/agent/advise',
      data: {
        'sme_id': smeId,
        'purchase_amount': purchaseAmount,
        'purchase_category': purchaseCategory,
        if (goal != null) 'goal': goal,
      },
    );
    return AgentAdvice.fromJson(res.data ?? {});
  }

  /// Upload CSV from raw bytes (works on web and mobile).
  Future<Map<String, dynamic>> uploadCsvBytes({
    required int smeId,
    required Uint8List bytes,
    required String fileName,
  }) async {
    final form = FormData.fromMap({
      'sme_id': smeId,
      'file': MultipartFile.fromBytes(bytes, filename: fileName),
    });
    final res = await _dio.post<Map<String, dynamic>>('/upload-csv', data: form);
    return res.data ?? {};
  }
}

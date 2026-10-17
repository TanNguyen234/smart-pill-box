part of 'smart_pill_api.dart';

/// Nhóm API Danh sách & Xử lý Cảnh báo (/api/alerts)
extension AlertsApi on SmartPillApi {
  Future<List<AlertItem>> alerts({
    int? patientId,
    String? status,
  }) async {
    final query = <String, String>{
      if (patientId != null) 'patient_id': '$patientId',
      if (status != null && status.isNotEmpty) 'status': status,
    };
    final data =
        await _request('/api/alerts', queryParameters: query) as List<dynamic>;
    return data
        .map((item) => AlertItem.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<AlertItem> updateAlert(
    int alertId, {
    required String status,
    String? note,
  }) async {
    final trimmedNote = note?.trim();
    final data = await _request(
      '/api/alerts/$alertId',
      method: 'PATCH',
      body: {
        'status': status,
        if (trimmedNote != null && trimmedNote.isNotEmpty) 'note': trimmedNote,
      },
    ) as Map<String, dynamic>;
    return AlertItem.fromJson(data);
  }
}

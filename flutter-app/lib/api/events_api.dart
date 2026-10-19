part of 'smart_pill_api.dart';

/// Nhóm API Lịch sử sự kiện hộp thuốc (/api/events)
extension EventsApi on SmartPillApi {
  Future<List<DeviceEventItem>> events({
    int? patientId,
    int? slot,
    String? date,
  }) async {
    final query = <String, String>{
      if (patientId != null) 'patient_id': '$patientId',
      if (slot != null) 'slot': '$slot',
      if (date != null && date.isNotEmpty) 'date': date,
    };
    final data =
        await _request('/api/events', queryParameters: query) as List<dynamic>;
    return data
        .map((item) => DeviceEventItem.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<int> clearEvents({int? patientId, int? slot}) async {
    final query = <String, String>{
      if (patientId != null) 'patient_id': '$patientId',
      if (slot != null) 'slot': '$slot',
    };
    final res = await _request('/api/events',
        method: 'DELETE', queryParameters: query) as Map<String, dynamic>;
    return (res['deleted_count'] as num?)?.toInt() ?? 0;
  }
}

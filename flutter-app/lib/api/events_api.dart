part of 'smart_pill_api.dart';

/// Nhóm API Lịch sử sự kiện hộp thuốc (/api/events) - Vai trò 5
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
}

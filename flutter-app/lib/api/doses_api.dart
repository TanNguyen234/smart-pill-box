part of 'smart_pill_api.dart';

/// Nhóm API Lần nhắc uống thuốc (/api/doses)
extension DosesApi on SmartPillApi {
  Future<List<DoseItem>> doses({
    int? patientId,
    String? date,
  }) async {
    final query = <String, String>{
      if (patientId != null) 'patient_id': '$patientId',
      if (date != null && date.isNotEmpty) 'date': date,
    };
    final data =
        await _request('/api/doses', queryParameters: query) as List<dynamic>;
    return data
        .map((item) => DoseItem.fromJson(item as Map<String, dynamic>))
        .toList();
  }
}

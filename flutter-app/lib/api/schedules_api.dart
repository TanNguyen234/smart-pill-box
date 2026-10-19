part of 'smart_pill_api.dart';

/// Nhóm API Hồ sơ & Lịch uống thuốc (/api/patients, /api/schedules)
extension SchedulesApi on SmartPillApi {
  Future<List<Patient>> patients() async =>
      (await _request('/api/patients') as List<dynamic>)
          .map((item) => Patient.fromJson(item as Map<String, dynamic>))
          .toList();

  Future<List<MedicationSchedule>> schedules() async =>
      (await _request('/api/schedules') as List<dynamic>)
          .map((item) =>
              MedicationSchedule.fromJson(item as Map<String, dynamic>))
          .toList();

  Future<void> createSchedule({
    required int patientId,
    required String medicationName,
    required int slot,
    required String time,
    String? daysOfWeek,
  }) async {
    await _request('/api/schedules', method: 'POST', body: {
      'patient_id': patientId,
      'medication_name': medicationName,
      'slot': slot,
      'time': time,
      'active': true,
      'days_of_week': ?daysOfWeek,
    });
  }

  Future<MedicationSchedule> updateSchedule(
    int scheduleId, {
    String? medicationName,
    int? slot,
    String? time,
    bool? active,
    String? daysOfWeek,
  }) async {
    final body = <String, dynamic>{};
    if (medicationName != null) body['medication_name'] = medicationName;
    if (slot != null) body['slot'] = slot;
    if (time != null) body['time'] = time;
    if (active != null) body['active'] = active;
    if (daysOfWeek != null) body['days_of_week'] = daysOfWeek;

    final data = await _request(
      '/api/schedules/$scheduleId',
      method: 'PATCH',
      body: body,
    ) as Map<String, dynamic>;
    return MedicationSchedule.fromJson(data);
  }

  Future<void> deleteSchedule(int scheduleId) async {
    await _request('/api/schedules/$scheduleId', method: 'DELETE');
  }
}

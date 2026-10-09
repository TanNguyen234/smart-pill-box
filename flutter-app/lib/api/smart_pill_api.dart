import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../models.dart';

const apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8000',
);

class ApiException implements Exception {
  const ApiException(this.message);
  final String message;

  @override
  String toString() => message;
}

class SmartPillApi {
  SmartPillApi({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;
  String? token;

  Future<dynamic> _request(String path, {String method = 'GET', Map<String, dynamic>? body}) async {
    final uri = Uri.parse('$apiBaseUrl$path');
    try {
      final response = await _client
          .send(http.Request(method, uri)
            ..headers.addAll({
              'Accept': 'application/json',
              'Content-Type': 'application/json',
              if (token != null) 'Authorization': 'Bearer $token',
            })
            ..body = body == null ? '' : jsonEncode(body))
          .timeout(const Duration(seconds: 8));
      final text = await response.stream.bytesToString();
      final data = text.isEmpty ? <String, dynamic>{} : jsonDecode(text);
      if (response.statusCode < 200 || response.statusCode >= 300) {
        final detail = data is Map<String, dynamic> ? data['detail'] : null;
        throw ApiException(detail is String ? detail : 'Máy chủ trả lỗi ${response.statusCode}.');
      }
      return data;
    } on SocketException {
      throw const ApiException('Không kết nối được máy chủ. Hãy kiểm tra backend và địa chỉ API.');
    } on TimeoutException {
      throw const ApiException('Máy chủ phản hồi quá lâu. Vui lòng thử lại.');
    } on FormatException {
      throw const ApiException('Máy chủ trả dữ liệu không hợp lệ.');
    }
  }

  Future<String> login(String email, String password) async {
    final data = await _request('/api/auth/login', method: 'POST', body: {'email': email, 'password': password}) as Map<String, dynamic>;
    token = data['access_token'] as String;
    return token!;
  }

  Future<Account> me() async => Account.fromJson(await _request('/api/me') as Map<String, dynamic>);

  Future<List<Patient>> patients() async => (await _request('/api/patients') as List<dynamic>)
      .map((item) => Patient.fromJson(item as Map<String, dynamic>))
      .toList();

  Future<List<MedicationSchedule>> schedules() async => (await _request('/api/schedules') as List<dynamic>)
      .map((item) => MedicationSchedule.fromJson(item as Map<String, dynamic>))
      .toList();

  Future<void> createSchedule({
    required int patientId,
    required String medicationName,
    required int slot,
    required String time,
  }) async {
    await _request('/api/schedules', method: 'POST', body: {
      'patient_id': patientId,
      'medication_name': medicationName,
      'slot': slot,
      'time': time,
      'active': true,
    });
  }

  Future<void> updateSchedule(int id, {bool? active}) async {
    await _request('/api/schedules/$id', method: 'PATCH', body: {
      if (active != null) 'active': active,
    });
  }
  
  void clearSession() => token = null;

  void close() => _client.close();
}

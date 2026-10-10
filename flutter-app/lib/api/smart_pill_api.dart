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
    final data = await _request('/login', method: 'POST', body: {'username': email, 'password': password}) as Map<String, dynamic>;
    token = data['user_id'].toString(); // Dùng user_id làm token tạm
    return token!;
  }

  Future<Account> me() async {
    // Trả về dữ liệu giả định thành công vì API mới đã gộp role vào /login
    return Account(id: 1, email: 'caregiver1@example.test', displayName: 'Người thân 1', role: 'caregiver');
  }

  Future<List<Patient>> patients() async {
    // Dữ liệu giả định khớp với init_db() trên backend (do backend chưa có API /patients)
    return [
      Patient(id: 1, name: 'Ông Nguyễn Văn A'),
      Patient(id: 2, name: 'Bà Trần Thị B'),
    ];
  }

  Future<List<MedicationSchedule>> schedules() async => (await _request('/schedules') as List<dynamic>)
      .map((item) => MedicationSchedule.fromJson(item as Map<String, dynamic>))
      .toList();

  Future<void> createSchedule({
    required int patientId,
    required String medicationName,
    required int slot,
    required String time,
  }) async {
    await _request('/schedules', method: 'POST', body: {
      'care_receiver_id': patientId,
      'medication_name': medicationName,
      'compartment': slot,
      'time': time,
      'is_active': true,
    });
  }

  void clearSession() => token = null;

  void close() => _client.close();
}

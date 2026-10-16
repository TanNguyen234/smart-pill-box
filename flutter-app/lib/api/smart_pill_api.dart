import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../models.dart';

part 'auth_api.dart';
part 'schedules_api.dart';
part 'events_api.dart';
part 'alerts_api.dart';

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

  Future<dynamic> _request(
    String path, {
    String method = 'GET',
    Map<String, String>? queryParameters,
    Map<String, dynamic>? body,
  }) async {
    final baseUri = Uri.parse('$apiBaseUrl$path');
    final uri = (queryParameters != null && queryParameters.isNotEmpty)
        ? baseUri.replace(queryParameters: queryParameters)
        : baseUri;
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

  void clearSession() => token = null;

  void close() => _client.close();
}

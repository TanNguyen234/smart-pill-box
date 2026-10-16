part of 'smart_pill_api.dart';

/// Nhóm API Xác thực & Tài khoản (/api/auth/login, /api/me)
extension AuthApi on SmartPillApi {
  Future<String> login(String email, String password) async {
    final data = await _request(
      '/api/auth/login',
      method: 'POST',
      body: {'email': email, 'password': password},
    ) as Map<String, dynamic>;
    token = data['access_token'] as String;
    return token!;
  }

  Future<Account> me() async =>
      Account.fromJson(await _request('/api/me') as Map<String, dynamic>);
}

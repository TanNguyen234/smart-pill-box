import 'package:flutter/material.dart';
import '../services/api_service.dart';

class AlertsScreen extends StatefulWidget {
  @override
  _AlertsScreenState createState() => _AlertsScreenState();
}

class _AlertsScreenState extends State<AlertsScreen> {
  final ApiService apiService = ApiService();
  late Future<List<dynamic>> futureAlerts;

  @override
  void initState() {
    super.initState();
    _loadAlerts();
  }

  void _loadAlerts() {
    setState(() {
      futureAlerts = apiService.fetchAlerts();
    });
  }

  void _showActionDialog(int alertId, String currentMessage) {
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text('Xử lý cảnh báo'),
          content: Text(currentMessage),
          actions: [
            TextButton(
              onPressed: () => _updateStatus(alertId, 'checked'),
              child: Text('Đã kiểm tra'),
            ),
            TextButton(
              onPressed: () => _updateStatus(alertId, 'assisted'),
              child: Text('Đã hỗ trợ', style: TextStyle(color: Colors.green)),
            ),
            TextButton(
              onPressed: () => _updateStatus(alertId, 'ignored'),
              child: Text('Bỏ qua', style: TextStyle(color: Colors.grey)),
            ),
          ],
        );
      },
    );
  }

  Future<void> _updateStatus(int alertId, String status) async {
    Navigator.pop(context); // Đóng hộp thoại dialog
    try {
      await apiService.updateAlertStatus(alertId, status);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Đã cập nhật trạng thái thành công')));
      _loadAlerts(); // Tải lại danh sách
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Lỗi cập nhật: $e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Danh sách Cảnh báo'), backgroundColor: Colors.redAccent),
      body: FutureBuilder<List<dynamic>>(
        future: futureAlerts,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return Center(child: CircularProgressIndicator());
          } else if (snapshot.hasError) {
            return Center(child: Text('Lỗi tải dữ liệu: ${snapshot.error}'));
          } else if (!snapshot.hasData || snapshot.data!.isEmpty) {
            return Center(child: Text('Hiện không có cảnh báo nào.'));
          }

          final alerts = snapshot.data!;
          return ListView.builder(
            itemCount: alerts.length,
            itemBuilder: (context, index) {
              final alert = alerts[index];
              bool isPending = alert['status'] == 'pending';
              Color statusColor = isPending ? Colors.red : Colors.green;
              
              return Card(
                margin: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: ListTile(
                  leading: Icon(Icons.warning, color: statusColor),
                  title: Text(alert['message'], style: TextStyle(fontWeight: isPending ? FontWeight.bold : FontWeight.normal)),
                  subtitle: Text('Trạng thái: ${alert['status']}\nThời gian: ${alert['timestamp']}'),
                  isThreeLine: true,
                  onTap: () {
                    if (isPending) {
                      _showActionDialog(alert['id'], alert['message']);
                    } else {
                      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Cảnh báo này đã được xử lý.')));
                    }
                  },
                ),
              );
            },
          );
        },
      ),
    );
  }
}

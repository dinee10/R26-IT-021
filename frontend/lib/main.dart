import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:uuid/uuid.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Ayurvedic Advisor',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        primarySwatch: Colors.green,
        scaffoldBackgroundColor: const Color(0xFFF8F9FA),
      ),
      home: const ChatScreen(),
    );
  }
}

class Message {
  final String text;
  final bool isUser;
  final bool hasCaution;
  Message({required this.text, required this.isUser, this.hasCaution = false});
}

// Maps a display label (shown in the UI) to the user_type value the
// backend's PERSONA_INSTRUCTIONS dict expects (see conversation_rag.py).
const Map<String, String> kUserTypes = {
  "General Public": "general_public",
  "Practitioner": "practitioner",
  "Student": "student",
  "Researcher": "researcher",
};

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _controller = TextEditingController();
  final List<Message> _messages = [];
  bool _isLoading = false;

  // NOTE: change this depending on where you run the app from — see the
  // "how to run" notes for the right value for emulator vs. physical device.
  final String backendUrl = "http://127.0.0.1:5000/api/ask";
  String sessionId = const Uuid().v4();

  String _selectedUserTypeLabel = "General Public";

  Map<String, dynamic> get userContext => {
        "user_type": kUserTypes[_selectedUserTypeLabel],
      };

  Future<void> sendMessage(String query) async {
    if (query.trim().isEmpty) return;

    setState(() {
      _messages.add(Message(text: query, isUser: true));
      _isLoading = true;
    });

    _controller.clear();

    try {
      final response = await http.post(
        Uri.parse(backendUrl),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "query": query,
          "session_id": sessionId,
          "user_context": userContext,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _messages.add(Message(
            text: data['answer'] ?? "Sorry, I couldn't get a response.",
            isUser: false,
            hasCaution: data['safety_context_available'] == true,
          ));
        });
      } else {
        setState(() {
          _messages.add(Message(text: "Server error: ${response.statusCode}", isUser: false));
        });
      }
    } catch (e) {
      setState(() {
        _messages.add(Message(text: "Cannot connect to backend. Is it running?", isUser: false));
      });
    } finally {
      setState(() => _isLoading = false);
    }
  }

  void _newConversation() {
    setState(() {
      _messages.clear();
      sessionId = const Uuid().v4();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("🌿 Ayurvedic Advisor"),
        backgroundColor: Colors.green[700],
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _newConversation,
            tooltip: "New Conversation",
          ),
        ],
      ),
      body: Column(
        children: [
          // --- User-type / persona selector ---
          // This is what drives persona-adaptive answers on the backend
          // (PERSONA_INSTRUCTIONS in conversation_rag.py).
          Container(
            width: double.infinity,
            color: Colors.green[50],
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Row(
              children: [
                const Text(
                  "Answering as: ",
                  style: TextStyle(fontSize: 13, color: Colors.black54),
                ),
                Expanded(
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: kUserTypes.keys.map((label) {
                        final bool selected = label == _selectedUserTypeLabel;
                        return Padding(
                          padding: const EdgeInsets.only(right: 8.0),
                          child: ChoiceChip(
                            label: Text(label, style: const TextStyle(fontSize: 12)),
                            selected: selected,
                            selectedColor: Colors.green[600],
                            labelStyle: TextStyle(
                              color: selected ? Colors.white : Colors.black87,
                            ),
                            onSelected: (_) {
                              setState(() => _selectedUserTypeLabel = label);
                            },
                          ),
                        );
                      }).toList(),
                    ),
                  ),
                ),
              ],
            ),
          ),

          Expanded(
            child: _messages.isEmpty
                ? const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.medical_services, size: 80, color: Colors.green),
                        SizedBox(height: 16),
                        Text(
                          "Ask about medicinal plants\nI can remember our conversation!",
                          style: TextStyle(fontSize: 16, color: Colors.grey),
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(12),
                    itemCount: _messages.length,
                    itemBuilder: (context, index) {
                      final msg = _messages[index];
                      return Align(
                        alignment: msg.isUser ? Alignment.centerRight : Alignment.centerLeft,
                        child: Container(
                          margin: const EdgeInsets.symmetric(vertical: 6),
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                          constraints: BoxConstraints(
                            maxWidth: MediaQuery.of(context).size.width * 0.78,
                          ),
                          decoration: BoxDecoration(
                            color: msg.isUser ? Colors.green[600] : Colors.grey[200],
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              if (!msg.isUser && msg.hasCaution)
                                Padding(
                                  padding: const EdgeInsets.only(bottom: 6),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.warning_amber_rounded,
                                          size: 16, color: Colors.orange[800]),
                                      const SizedBox(width: 4),
                                      Text(
                                        "Includes a safety caution",
                                        style: TextStyle(
                                          fontSize: 11,
                                          fontWeight: FontWeight.bold,
                                          color: Colors.orange[800],
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              Text(
                                msg.text,
                                style: TextStyle(
                                  color: msg.isUser ? Colors.white : Colors.black87,
                                  fontSize: 16,
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
          ),

          if (_isLoading)
            const Padding(padding: EdgeInsets.all(8.0), child: CircularProgressIndicator()),

          Padding(
            padding: const EdgeInsets.all(12.0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    decoration: InputDecoration(
                      hintText: "Ask about plants or diseases...",
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(25)),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                    ),
                    onSubmitted: sendMessage,
                  ),
                ),
                const SizedBox(width: 8),
                FloatingActionButton(
                  onPressed: () => sendMessage(_controller.text),
                  backgroundColor: Colors.green[700],
                  child: const Icon(Icons.send, color: Colors.white),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
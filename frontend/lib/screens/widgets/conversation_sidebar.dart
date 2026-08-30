import 'package:flutter/material.dart';

import '../services/conversation_store.dart';
import '../../theme/app_colors.dart';

class ConversationSidebar extends StatelessWidget {
  final String userType;
  final String personaLabel;
  final String? activeConversationId;
  final Color accentColor;
  final void Function(String conversationId) onSelect;
  final VoidCallback onNewConversation;

  const ConversationSidebar({
    super.key,
    required this.userType,
    required this.personaLabel,
    required this.activeConversationId,
    required this.accentColor,
    required this.onSelect,
    required this.onNewConversation,
  });

  Future<void> _confirmDelete(BuildContext context, String id, String title) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Delete conversation?"),
        content: Text('"$title" will be removed from this session.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text("Cancel"),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text("Delete", style: TextStyle(color: AppColors.danger)),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      ConversationStore.instance
          .deleteConversation(userType: userType, conversationId: id);
      if (activeConversationId == id) {
        onNewConversation();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Drawer(
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
              child: Text(
                "$personaLabel chats",
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 18,
                  color: AppColors.text,
                ),
              ),
            ),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 16),
              child: Text(
                "Cleared when the app restarts",
                style: TextStyle(fontSize: 11, color: AppColors.muted),
              ),
            ),
            const SizedBox(height: 8),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: ElevatedButton.icon(
                onPressed: () {
                  onNewConversation();
                  Navigator.pop(context);
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: accentColor,
                  foregroundColor: Colors.white,
                ),
                icon: const Icon(Icons.add),
                label: const Text("New conversation"),
              ),
            ),
            const Divider(height: 24),
            Expanded(
              child: ListenableBuilder(
                listenable: ConversationStore.instance,
                builder: (context, _) {
                  final conversations =
                      ConversationStore.instance.conversationsFor(userType);
                  if (conversations.isEmpty) {
                    return const Padding(
                      padding: EdgeInsets.all(16),
                      child: Text(
                        "No conversations yet this session.",
                        style: TextStyle(color: AppColors.muted),
                      ),
                    );
                  }
                  return ListView.builder(
                    itemCount: conversations.length,
                    itemBuilder: (context, index) {
                      final convo = conversations[index];
                      final isActive = convo.id == activeConversationId;
                      return ListTile(
                        selected: isActive,
                        selectedTileColor: accentColor.withOpacity(0.08),
                        leading: Icon(Icons.chat_bubble_outline,
                            color: isActive ? accentColor : AppColors.muted, size: 20),
                        title: Text(
                          convo.title,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 14),
                        ),
                        trailing: IconButton(
                          icon: const Icon(Icons.delete_outline,
                              size: 20, color: AppColors.muted),
                          onPressed: () =>
                              _confirmDelete(context, convo.id, convo.title),
                        ),
                        onTap: () {
                          onSelect(convo.id);
                          Navigator.pop(context);
                        },
                      );
                    },
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
import 'dart:async';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../theme/app_colors.dart';
import '../widgets/app_buttons.dart';
import '../widgets/app_text_field.dart';
import '../widgets/user_avatar.dart';

class EditProfilePage extends StatefulWidget {
  const EditProfilePage({super.key});

  @override
  State<EditProfilePage> createState() => _EditProfilePageState();
}

class _EditProfilePageState extends State<EditProfilePage> {
  late final TextEditingController _nameController;
  bool _saving = false;
  bool _uploadingPhoto = false;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(
      text: FirebaseAuth.instance.currentUser?.displayName ?? '',
    );
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  Future<void> _saveProfile() async {
    setState(() => _saving = true);

    try {
      await FirebaseAuth.instance.currentUser?.updateDisplayName(
        _nameController.text.trim(),
      );
      await FirebaseAuth.instance.currentUser?.reload();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Profile updated.')),
        );
        Navigator.of(context).pop(true);
      }
    } on FirebaseAuthException catch (error) {
      _showMessage(error.message ?? 'Could not update profile.');
    } catch (_) {
      _showMessage('Something went wrong. Please try again.');
    } finally {
      if (mounted) {
        setState(() => _saving = false);
      }
    }
  }

  Future<void> _changeProfilePhoto() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      _showMessage('Please log in again before changing your photo.');
      return;
    }

    final pickedImage = await ImagePicker().pickImage(
      source: ImageSource.gallery,
      maxWidth: 512,
      maxHeight: 512,
      imageQuality: 85,
    );

    if (pickedImage == null) {
      return;
    }

    setState(() => _uploadingPhoto = true);

    try {
      final imageBytes = await pickedImage.readAsBytes();
      final storageRef = FirebaseStorage.instance
          .ref()
          .child('users')
          .child(user.uid)
          .child('profile-photo.jpg');

      await storageRef
          .putData(
            imageBytes,
            SettableMetadata(contentType: 'image/jpeg'),
          )
          .timeout(const Duration(seconds: 20));

      final photoUrl = await storageRef
          .getDownloadURL()
          .timeout(const Duration(seconds: 10));
      await user.updatePhotoURL(photoUrl);
      await user.reload();

      if (mounted) {
        setState(() {});
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Profile photo updated.')),
        );
      }
    } on FirebaseException catch (error) {
      _showMessage(error.message ?? 'Could not upload profile photo.');
    } on TimeoutException {
      _showMessage(
        'Upload timed out. Check Firebase Storage setup and connection.',
      );
    } catch (_) {
      _showMessage('Could not upload profile photo. Please try again.');
    } finally {
      if (mounted) {
        setState(() => _uploadingPhoto = false);
      }
    }
  }

  void _showMessage(String message) {
    if (!mounted) {
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  @override
  Widget build(BuildContext context) {
    final user = FirebaseAuth.instance.currentUser;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Edit Profile'),
        centerTitle: false,
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 16, 24, 32),
          children: [
            Center(
              child: EditableProfilePhoto(
                user: user,
                uploading: _uploadingPhoto,
                onPressed: _uploadingPhoto ? null : _changeProfilePhoto,
              ),
            ),
            const SizedBox(height: 10),
            Center(
              child: TextButton.icon(
                onPressed: _uploadingPhoto ? null : _changeProfilePhoto,
                icon: const Icon(Icons.photo_camera_outlined, size: 18),
                label: Text(_uploadingPhoto ? 'Uploading photo' : 'Change photo'),
              ),
            ),
            const SizedBox(height: 28),
            const FieldLabel('Full Name'),
            AppTextField(
              controller: _nameController,
              hintText: 'Your name',
              icon: Icons.person_outline_rounded,
            ),
            const SizedBox(height: 18),
            const FieldLabel('Email Address'),
            ReadOnlyProfileField(
              icon: Icons.mail_outline_rounded,
              value: user?.email ?? 'No email connected',
            ),
            const SizedBox(height: 28),
            PrimaryButton(
              label: _saving ? 'Saving' : 'Save Changes',
              icon: Icons.check_rounded,
              onPressed: _saving ? null : _saveProfile,
            ),
          ],
        ),
      ),
    );
  }
}

class EditableProfilePhoto extends StatelessWidget {
  const EditableProfilePhoto({
    super.key,
    required this.user,
    required this.uploading,
    required this.onPressed,
  });

  final User? user;
  final bool uploading;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return Stack(
      clipBehavior: Clip.none,
      children: [
        UserAvatar(user: user, radius: 52),
        Positioned(
          right: -2,
          bottom: -2,
          child: IconButton.filled(
            onPressed: onPressed,
            style: IconButton.styleFrom(
              backgroundColor: AppColors.primary,
              foregroundColor: Colors.white,
              fixedSize: const Size(40, 40),
            ),
            icon: uploading
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Icon(Icons.camera_alt_rounded, size: 20),
          ),
        ),
      ],
    );
  }
}

class ReadOnlyProfileField extends StatelessWidget {
  const ReadOnlyProfileField({
    super.key,
    required this.icon,
    required this.value,
  });

  final IconData icon;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minHeight: 56),
      padding: const EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(
        color: const Color(0xFFF7F9F7),
        border: Border.all(color: AppColors.border),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          Icon(icon, color: AppColors.muted),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              value,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: AppColors.muted,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

import 'dart:typed_data';

import 'package:cross_file/cross_file.dart';

Future<XFile> writePdfBytes(Uint8List bytes, String name) async {
  return XFile.fromData(bytes, name: name, mimeType: 'application/pdf');
}

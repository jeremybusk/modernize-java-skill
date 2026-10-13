package example;

import java.nio.charset.StandardCharsets;
import java.util.zip.Deflater;

public final class Compression {
    public static byte[] compress(String value) {
        Deflater deflater = new Deflater();
        try {
            byte[] input = value.getBytes(StandardCharsets.UTF_8);
            deflater.setInput(input);
            deflater.finish();
            byte[] output = new byte[input.length + 100];
            int count = deflater.deflate(output);
            return java.util.Arrays.copyOf(output, count);
        } finally {
            deflater.end();
        }
    }
}

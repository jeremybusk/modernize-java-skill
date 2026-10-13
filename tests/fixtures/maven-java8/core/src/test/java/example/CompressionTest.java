package example;

import java.nio.charset.StandardCharsets;
import java.util.zip.Inflater;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

class CompressionTest {
    @Test void preservesWireData() throws Exception {
        String input = "hello modernization: café";
        Inflater inflater = new Inflater();
        try {
            inflater.setInput(Compression.compress(input));
            byte[] output = new byte[1000];
            int count = inflater.inflate(output);
            assertEquals(input, new String(output, 0, count, StandardCharsets.UTF_8));
        } finally {
            inflater.end();
        }
    }
}

package example;

public class Main {
    public static void main(String[] args) {
        if (Compression.compress("hello modernization").length == 0) {
            throw new IllegalStateException("Empty wire payload");
        }
        System.out.println("MIGRATION_OK");
    }
}

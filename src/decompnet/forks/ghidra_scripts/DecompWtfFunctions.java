// decomp.wtf: list every function's entry VA and body size, one JSON object per line:
// {"name": "...", "va": 4198400, "size": 42}. No decompilation — just auto-analysis + the function list,
// so it is fast enough to run at import time (needed to onboard STRIPPED binaries, which have no symbols).
// Run by analyzeHeadless as a post-script; the output path is its argument.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;

import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;

public class DecompWtfFunctions extends GhidraScript {
    private static String quote(String s) {
        StringBuilder b = new StringBuilder("\"");
        for (char c : s.toCharArray()) {
            switch (c) {
                case '"': b.append("\\\""); break;
                case '\\': b.append("\\\\"); break;
                case '\n': b.append("\\n"); break;
                case '\r': break;
                case '\t': b.append("\\t"); break;
                default:
                    if (c < 0x20) b.append(String.format("\\u%04x", (int) c)); else b.append(c);
            }
        }
        return b.append('"').toString();
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        try (PrintWriter w = new PrintWriter(new OutputStreamWriter(new FileOutputStream(args[0]), StandardCharsets.UTF_8))) {
            FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
            while (it.hasNext() && !monitor.isCancelled()) {
                Function f = it.next();
                if (f.isExternal() || f.isThunk()) continue;
                long va = f.getEntryPoint().getOffset();
                // Span from entry to the body's max address (handles contiguous bodies exactly; a
                // non-contiguous body is slightly over-counted, which only the odd split function hits).
                long end = f.getBody().getMaxAddress().getOffset();
                long size = end - va + 1;
                if (size <= 0) continue;
                w.println("{\"name\": " + quote(f.getName()) + ", \"va\": " + va + ", \"size\": " + size + "}");
            }
        }
    }
}

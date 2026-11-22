import re

p = "engine/src/program/generate.cpp"
src = open(p).read()

old = (
    "                        pools_budget.shrink((size_t) -1);\n"
    "                        limits.admit = [floor, &o](uint64_t need, std::string& w) {\n"
    "                            const auto mem = strata::core::sample_host_memory();\n"
    "                            if (strata::core::conversation_memory_admit(mem ? std::optional<uint64_t>(mem->available) : std::nullopt,\n"
    "                                                                        need, floor)) return true;\n"
    "                            w = \"not enough RAM to read it (\" + std::to_string(need >> 20) + \" MiB plus a floor of \" +\n"
    "                                std::to_string((long long) o.conversation_cache_min_free_mib) + \" MiB needed, \" + ram_note(mem) + \")\";\n"
    "                            return false;\n"
    "                        };"
)

new = (
    "                        pools_budget.shrink((size_t) -1);\n"
    "                        // Port of the fork patch, brought in line with the parking gate above: the\n"
    "                        // tier-read gate only shrank the park pools once and then refused. Freed memory\n"
    "                        // can stay in the C library heap, which /proc/meminfo does not count, and an\n"
    "                        // evicted parked conversation only gives its RAM back once the spill writer has\n"
    "                        // written it out and its bytes are reclaimed.\n"
    "                        limits.admit = [&](uint64_t need, std::string& w) {\n"
    "                            auto ram_ok = [&]() {\n"
    "                                const auto m = strata::core::sample_host_memory();\n"
    "                                return m && strata::core::conversation_memory_admit(\n"
    "                                    std::optional<uint64_t>(m->available), need, floor);\n"
    "                            };\n"
    "                            for (size_t n = 0; n <= conversations.slots(); ++n) {\n"
    "                                if (ram_ok()) return true;\n"
    "                                if (pools_budget.idle_bytes() > 0) {\n"
    "                                    pools_budget.shrink((size_t) -1);\n"
    "                                    if (ram_ok()) { std::fprintf(stderr, \"strata serve: tier read admitted after pool shrink\\\\n\"); return true; }\n"
    "                                }\n"
    "                                if (strata::core::release_free_heap() && ram_ok()) {\n"
    "                                    std::fprintf(stderr, \"strata serve: tier read admitted after heap reclaim\\\\n\");\n"
    "                                    return true;\n"
    "                                }\n"
    "                                if (n == conversations.slots() || !conversations.evict_oldest()) {\n"
    "                                    const auto mem = strata::core::sample_host_memory();\n"
    "                                    w = \"not enough RAM to read it (\" + std::to_string(need >> 20) +\n"
    "                                        \" MiB plus a floor of \" + std::to_string((long long) o.conversation_cache_min_free_mib) +\n"
    "                                        \" MiB needed, \" + ram_note(mem) + \")\";\n"
    "                                    return false;\n"
    "                                }\n"
    "                                // the victim went to the background writer: its RAM is back only once\n"
    "                                // written and reclaimed, exactly as the parking gate does\n"
    "                                if (spill_writer) {\n"
    "                                    spill_writer->wait_idle();\n"
    "                                    spill_reclaim();\n"
    "                                }\n"
    "                            }\n"
    "                            return false;\n"
    "                        };"
)

n = src.count(old)
print("matches:", n)
assert n == 1
open(p, "w").write(src.replace(old, new))
print("patched with writer drain")


for TYPE in "Leaderboard" "Final"; do
    for BENCHMARK_KIND in "GHTS" "CHS"; do
        python collect_benchmark.py --benchmark_root  ~/BENCHMARK_PROCESSED/${BENCHMARK_KIND}/${TYPE}/\
            --out_dir ~/BENCHMARK_CONFIGS/${BENCHMARK_KIND}/${TYPE}/\
            --benchmark_name ${BENCHMARK_KIND}_${TYPE}\
            --benchmark_kind ${BENCHMARK_KIND}\
            --scorers ../data/peaks_scorers.json
    done
done
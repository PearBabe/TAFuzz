initially { int x = 0; }

transition[cost=5] t [0,1] when (x == 0) { x = 1; }

cost_rate 1

check[no_trace] mincost (x == 1)

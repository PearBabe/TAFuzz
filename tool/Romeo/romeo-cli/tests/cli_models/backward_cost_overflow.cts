initially { int x = 0; }

transition[cost=1073741823] t [0,1] when (x == 0) { x = 1; }

check[zones,no_trace] mincost (x == 1)

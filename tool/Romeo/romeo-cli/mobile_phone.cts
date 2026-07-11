typedef enum { low, high, win, reset } astate_t;
typedef enum { X, Y } jstate_t;
typedef enum { zero, fiveplus, sixplus, tenplus } cstatex_t;
typedef enum { zero, twoplus,  sixplus, tenplus } cstatey_t;

int costr(astate_t sx, astate_t sy)
{
  int cx = 0;
  int cy = 0;

  if (sx == low) { cx = 1; } else if (sx == high) { cx = 10; }
  if (sy == low) { cy = 2; } else if (sy == high) { cy = 20; }

  return cx + cy;
}

initially
{
  jstate_t statej = X; 
  astate_t statex = low; 
  astate_t statey = low;
  cstatex_t clockx = zero;
  cstatey_t clocky = zero;
}

transition[control=u] jamtox 
  when (statej == Y and statex == low and (clocky == sixplus or clocky == tenplus)) 
    { statej = X; statex = high; clockx = zero;}

transition[control=u] jaminx_l 
  when (statej == X and statex == low and (clockx == sixplus or clockx == tenplus)) 
    { statex = high; clockx = zero; }

transition[control=u] jamtoy 
  when (statej == X and statey == low and (clockx == sixplus or clockx == tenplus)) 
    { statej = X; statey = high; clocky = zero; }

transition[control=u] jaminy_l 
  when (statej == Y and statey == low and (clocky == sixplus or clocky == tenplus)) 
    { statey = high; clocky = zero; }

transition[control=u] jaminx_h 
  when (statej == X and statex == high and (clockx == sixplus or clockx == tenplus)) 
    { clockx = zero; }

transition[control=u] jaminy_h 
  when (statej == Y and statey == high and (clocky == sixplus or clocky == tenplus)) 
    { clocky = zero; }

transition h_to_l_x 
  when (statex == high and clockx != zero) 
    { statex = low; clocky = zero; }

transition h_to_l_y 
  when (statey == high and clocky != zero) 
    { statey = low; clockx = zero; }

transition[cost=7] winx when (statex == low and clockx == tenplus) { statex = win; }
transition[cost=1] winy when (statey == low and clocky == tenplus) { statey = win; }

transition x5  [5, 5] when (clockx == zero) { clockx = fiveplus; }
transition[control=u] x6u  (1, 2) when (clockx == fiveplus) { clockx = sixplus; }
transition x6  (1, 2) when (clockx == fiveplus) { clockx = sixplus; }
transition x10 [5, 5] when (clockx == sixplus or clockx == fiveplus) { clockx = tenplus; }
// transition x6  [2, 2] when (clockx == fiveplus) { clockx = sixplus; }
// transition x10 [3, 3] when (clockx == sixplus) { clockx = tenplus; }

transition y2  [2, 2] when (clocky == zero) { clocky = twoplus; }
transition y6  (4, 5) when (clocky == twoplus) { clocky = sixplus; }
transition[control=u] y6u  (4, 5) when (clocky == twoplus) { clocky = sixplus; }
transition y10 [8, 8] when (clocky == sixplus or clocky == twoplus) { clocky = tenplus; }
// transition y6  [5, 5] when (clocky == twoplus) { clocky = sixplus; }
// transition y10 [3, 3] when (clocky == sixplus) { clocky = tenplus; }

transition[speed=2] dummy when (false) {}

cost_rate costr(statex, statey)

simulate[zones]
// check[timed_trace] mincost (statex == win or statey == win)
check[zones, no_trace] control (statex == win or statey == win)

#include "MightyPPL.h"

namespace mightypplcpp {

    bool canonical_projection_enabled = false;
    bool scale_product_bounds_by_gcd = true;
    size_t canonical_projection_max_valuations = 4096;
    size_t last_projection_valuation_count = 0;
    std::string last_nnf_formula;
    std::map<std::string, int> last_props_by_name;

}

//
// Created by jan on 11.4.19.
//

#include "automaton.hpp"
#include <functional>

string baseFileName(const string &s) {
    return s.substr(s.find_last_of("/\\") + 1);
}

void Automaton::consumeState(const ProgramState &state) {
    if (current_state == nullptr || this->isInIllegalState()) {
        this->illegal_state = true;
        return;
    }

    if (current_state->is_violation || current_state->is_sink) {
        // don't do anything once we have reached violation or sink
        return;
    }
    const auto &succs = successor_rel.find(current_state->id);
    if (succs == successor_rel.end()) { // state isn't sink
        this->illegal_state = true;
        return;
    }

    for (const auto &edge: succs->second) {
        if (baseFileName(edge->origin_file) == baseFileName(state.origin_file) &&
            edge->start_line == state.start_line) {
            // check control branch
            if (edge->controlCondition != ConditionUndefined || state.control != ConditionUndefined) {
                if (edge->controlCondition == state.control) {
                    current_state = nodes.find(edge->target_id)->second;
//                    printf("\tTaking edge: %s --> %s\n", edge->source_id.c_str(), edge->target_id.c_str());
                    return;
                } else {
                    continue;
                }
            }
            current_state = nodes.find(edge->target_id)->second;
//            printf("\tTaking edge: %s --> %s\n", edge->source_id.c_str(), edge->target_id.c_str());
            return;
        }
    }

}
//
// Created by jan svejda on 3.4.19.
//

#ifndef CWVALIDATOR_AUTOMATON_HPP
#define CWVALIDATOR_AUTOMATON_HPP

#include <stdbool.h>
#include <stddef.h>
#include "../utils/pugixml/pugixml.hpp"
#include <string>
#include <deque>
#include <vector>
#include <map>
#include <functional>
#include <memory>

using namespace std;

class Node {
public:
    string id;
    string node_type;
    string invariant;
    string invariant_scope;
    bool is_entry{};
    bool is_violation{};
    bool is_sink{};
    bool is_frontier{};
    size_t thread_number{};

    void print();
};

class Edge {
public:
    string source_id;
    string target_id;
    string origin_file;
    string assumption;
    string assumption_scope;
    string assumption_result_function;
    string enter_function;
    string return_from_function;
    string source_code;
    string control;
    size_t start_line;
    bool enterLoopHead;

    void print();
};

struct Data;

class Automaton {
public:
    Automaton(vector<Node> nodes, vector<Edge> edges, shared_ptr<Data>& data);

    vector<Node> nodes;
    vector<Edge> edges;
    shared_ptr<Data> data;
};

struct Key {
    string name;
    string type;
    string for_;
    string id;
    string default_val;

    Key() : name(""), type(""), for_(""), id(""), default_val("") {}

    static void printKey(Key *k) {
        printf("name: %s\ttype: %s\tfor: %s\tid: %s\tdef: %s\n", k->name.c_str(), k->type.c_str(), k->for_.c_str(),
               k->id.c_str(), k->default_val.c_str());
    }
};

struct DefaultKeyValues {
    void addKey(const Key& k);
    const Key getDefault(const string& id) const;

    void print();

private:
    map<string, Key> default_keys;
};

struct Data {
    string source_code_lang;
    string program_file;
    string program_hash;
    string specification;
    string architecture;
    string producer;
    string witness_type;

    void print();
};

shared_ptr<Automaton> automatonFromWitness(const pugi::xml_document &doc);

#endif //CWVALIDATOR_AUTOMATON_HPP

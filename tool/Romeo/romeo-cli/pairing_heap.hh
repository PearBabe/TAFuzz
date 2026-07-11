/* This file is part of the Roméo model-checking software

Copyright École Centrale de Nantes, LS2N

Contributors: Didier Lime (2014-2025)

Didier.Lime@ec-nantes.fr

This software is a computer program whose purpose is to perform
parametric model checking on timed and hybrid systems.

This software is governed by the CeCILL license under French law and
abiding by the rules of distribution of free software.  You can  use, 
modify and/ or redistribute the software under the terms of the CeCILL
license as circulated by CEA, CNRS and INRIA at the following URL
"http://www.cecill.info". 

As a counterpart to the access to the source code and  rights to copy,
modify and redistribute granted by the license, users are provided only
with a limited warranty  and the software's author,  the holder of the
economic rights,  and the successive licensors  have only  limited
liability. 

In this respect, the user's attention is drawn to the risks associated
with loading,  using,  modifying and/or developing or reproducing the
software by the user in light of its specific status of free software,
that may mean  that it is complicated to manipulate,  and  that  also
therefore means  that it is reserved for developers  and  experienced
professionals having in-depth computer knowledge. Users are therefore
encouraged to load and test the software's suitability as regards their
requirements in conditions enabling the security of their systems and/or 
data to be ensured and,  more generally, to use and operate it in the 
same conditions as regards security. 

The fact that you are presently reading this means that you have had
knowledge of the CeCILL license and that you accept its terms. */

#ifndef PAIRING_HEAP_HH
#define PAIRING_HEAP_HH

#include <iostream>
#include <list>
#include <cstdlib>
#include <map>

#include <logger.hh> 
extern romeo::Logger Log;

namespace romeo
{

    template<typename T, class CMP> class PHIterator;

    template <typename T, class CMP=std::less<T> > class PHNode
    {
        private:
            T key;
            PHNode<T, CMP>* parent;
            PHNode<T, CMP>* child;
            PHNode<T, CMP>* sibling;
            CMP compare;

        public:
            PHNode(const T& x): key(x), parent(nullptr), child(nullptr), sibling(nullptr)
            {
            }

            void add_child(PHNode<T, CMP>* n)
            {
                n->parent = this;
                if (child != nullptr)
                {
                    child->parent = n;
                    n->sibling = child;
                }
                child = n;
            }

            PHNode<T, CMP>* merge_with(PHNode<T, CMP>* n)
            {
                PHNode<T, CMP>* result = this;

                if (n != nullptr)
                {
                    if (compare(n->key, key))
                    {
                        n->add_child(this);
                        result = n;
                    } else {
                        this->add_child(n);
                    }
                } 

                return result;
            }

            PHNode<T, CMP>* insert(PHNode<T, CMP>* x)
            {
                return merge_with(x);
            }


            T find_min() const
            {
                return key;
            }

            PHNode<T, CMP>* pairing_merge()
            {
                PHNode<T, CMP> * result = this;
                if (sibling != nullptr)
                {
                    PHNode<T, CMP>* S = sibling;
                    PHNode<T, CMP>* m = S->sibling;

                    parent = nullptr;
                    sibling = nullptr;
                    S->sibling = nullptr;
                    S->parent = nullptr;

                    result = this->merge_with(S);
                    if (m != nullptr)
                    {
                        result = result->merge_with(m->pairing_merge());
                    }
                }

                return result;
            }

            PHNode<T, CMP>* delete_min()
            {
                if (child != nullptr)
                {
                    return child->pairing_merge();
                } else {
                    return nullptr;
                }
            }

            PHNode<T, CMP>* delete_node()
            {
                PHNode<T, CMP>* p = parent;
                PHNode<T, CMP>* s = sibling;
                PHNode<T, CMP> * r = delete_min();
                if (r == nullptr)
                {
                    r = s;
                } else {
                    r->sibling = s;
                    if (s != nullptr)
                    {
                        s->parent = r;
                    }
                }

                if (r != nullptr)
                {
                    r->parent = p;
                }
                if (p != nullptr)
                {
                    if (p->sibling == this)
                    {
                        p->sibling = r;
                    } else {
                        p->child = r;
                    }
                }

                return r;
            }

            void print_debug() const
            {
                std::cout << "key: " << key << std::endl;
                if (child != nullptr)
                {
                    std::cout << "child " << child->key  << (child->parent != this? "!": "")<< std::endl;
                }
                if (sibling != nullptr)
                {
                    std::cout << "sibling " << sibling->key << (sibling->parent != this? "!": "") << std::endl;
                }
                if (parent != nullptr)
                {
                    std::cout << "parent " << parent->key << std::endl;
                }
                if (child != nullptr)
                {
                    child->print_debug();
                }
                if (sibling != nullptr)
                {
                    sibling->print_debug();
                }
            }

            bool is_consistent()
            {
                return ((child   == nullptr || child->parent   == this)
                     && (sibling == nullptr || sibling->parent == this));
            }

            // Destroy only heap wrapper nodes.  Stored values are owned by
            // their passed set / caller and may already have been released.
            static void destroy_tree(PHNode<T, CMP>* root)
            {
                std::list<PHNode<T, CMP>*> waiting;
                if (root != nullptr)
                {
                    waiting.push_back(root);
                }

                while (!waiting.empty())
                {
                    PHNode<T, CMP>* current = waiting.front();
                    waiting.pop_front();
                    if (current->child != nullptr)
                    {
                        waiting.push_back(current->child);
                    }
                    if (current->sibling != nullptr)
                    {
                        waiting.push_back(current->sibling);
                    }
                    delete current;
                }
            }

        friend class PHIterator<T, CMP>;
    };

    template<typename T, class CMP=std::less<T> > class PHIterator
    {
        private:
            std::list<PHNode<T, CMP>*> waiting;

        public:
            PHIterator(PHNode<T, CMP>* n) 
            {
                if (n != nullptr)
                {
                    waiting.push_back(n);
                }
            }

            void next()
            {
                if (!waiting.empty())
                {
                    PHNode<T, CMP>* t = waiting.front();
                    waiting.pop_front();
                    if (t->child != nullptr)
                    {
                        waiting.push_back(t->child);
                    }
                    if (t->sibling != nullptr)
                    {
                        waiting.push_back(t->sibling);
                    }
                }
            }

            bool done()
            {
                return waiting.empty();
            }

            PHNode<T, CMP>* current_node() const
            {   
                if (!waiting.empty())
                {
                    return waiting.front();
                } else {
                    return nullptr;
                }
            }

            T& operator*() const
            {
                PHNode<T, CMP>* n = current_node();
                if (n != nullptr)
                {
                    return n->key;
                } else {
                    std::cerr << "cannot access element in iterator" << std::endl;
                    exit(1);
                }
            }

            void replace(PHNode<T, CMP>* n)
            {
                waiting.pop_front();
                if (n != nullptr)
                {
                    waiting.push_front(n);
                }
            }
    };

    template <typename T, class CMP=std::less<T> > class PairingHeap
    {
        private:
            PHNode<T, CMP>* root;
            std::map<T, PHNode<T, CMP>*> unique;

        public:
            PairingHeap(): root(nullptr)
            {
            }

            bool is_empty() const
            {
                return (root == nullptr);
            }

            void insert(const T& x)
            {
                PHNode<T, CMP>* p = new PHNode<T, CMP>(x);
                auto r = unique.insert(std::pair<T, PHNode<T, CMP>*>(x, p));
                
                if (r.second) // was actually inserted (not already existent)
                {
                    if (root != nullptr)
                    {
                        root = root->insert(p);
                    } else {
                        root = p;
                    }
                } else {
                    delete p;
                }
            }

            T top() const
            {
                if (root != nullptr)
                {
                    return root->find_min();
                } else {
                    std::cerr << "Empty heap has no minimum element." << std::endl;
                    exit(1);
                }
            }

            T pop()
            {
                T m = root->find_min();
                unique.erase(m);

                PHNode<T, CMP>* old = root;
                root = root->delete_min();

                delete old;

                return m;
            }

            PHNode<T, CMP>* delete_node(PHNode<T, CMP>* n)
            {
                if (n == root)
                {
                    pop();
                    return root;
                } else {
                    unique.erase(n->find_min());
                    PHNode<T, CMP>* r = n->delete_node();
                    delete n;

                    return r;
                }
            }

            void erase(PHIterator<T, CMP>& i)
            {
                i.replace(delete_node(i.current_node()));
            }

            PHIterator<T, CMP> iterator() const
            {
                return PHIterator<T, CMP>(root);
            }

            void print_debug() const
            {
                if (root == nullptr)
                {
                    std::cout << "empty" << std::endl;
                } else {
                    root->print_debug();
                }
            }

            bool delete_value(const T& x)
            {
                auto i = unique.find(x);
                if (i != unique.end())
                {
                    delete_node(i->second);

                    return true;
                }

                return false;

                //PHIterator<T, CMP> i = iterator();
                //while (!i.done())
                //{
                //    if (*i == x)
                //    {
                //        erase(i);
                //        return true;
                //    } else {
                //        i.next();
                //    }
                //}

                //return false;
            }
            
            //bool delete_value_all(const T& x)
            //{
            //    bool r = false;
            //    PHIterator<T, CMP> i = iterator();
            //    while (!i.done())
            //    {
            //        if (*i == x)
            //        {
            //            erase(i);
            //            r = true;
            //        } else {
            //            i.next();
            //        }
            //    }

            //    return r;
            //}
            
            bool is_consistent()
            {
                PHIterator<T, CMP> i = iterator();
                while (!i.done())
                {
                    if (!i.current_node()->is_consistent())
                    {
                        return false;
                    }
                    i.next();
                }

                return true;
            }

            ~PairingHeap()
            {
                if (root != nullptr)
                {
                    PHNode<T, CMP>::destroy_tree(root);
                    root = nullptr;
                }
                unique.clear();
            }
    };

}

#endif

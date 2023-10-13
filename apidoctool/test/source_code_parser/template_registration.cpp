// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

#include <functional>
#include "pool.h"

void registerRestHandlers(Pool* const p)
{
    using namespace std::placeholders;

    /**%apidoc GET /foo/bar
     * Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec a diam lectus. Sed sit amet
     * ipsum mauris. Maecenas congue ligula ac quam viverra nec consectetur ante hendrerit.
     * %param[default] var1 Lorem ipsum dolor sit amet, consectetur adipiscing elit.
     * %return Maecenas congue ligula ac.
     * %// LoremIpsum::DolorSitAmet
     */
    regGet<nullptr_t, LoremIpsum>(p, Lorem::Ipsum);

    // LoremIpsumManager::quidamUtErat
    regUpdate<LoremIspumData>(p, Lorem::ipsumDolorSitamet);

    /**%apidoc GET /foo/baz
     * Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat.
     * %param[default] format
     * %param var1 Lorem ipsum dolor sit amet, consectetur adipiscing elit.
     * %return Excepteur sint occaecat cupidatat non proident.
     * %// LoremIpsum::AnimIdEst
     */
    regGet<SomeVarType, SomeOtherType>(p, Lorem::ullamcoLaborisNisiUtAliquipExea);

    /**%apidoc[proprietary] POST /foo/blabla
     * Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea.
     * Quis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla.
     * %return Xcepteur sint occaecat cupidatat non proident.
     */
    regUpdate<LoremType>(p, Lorem::blablaAction);

    /**%apidoc GET /foo/functorBlah
     * Proin ut ligula vel nunc egestas porttitor. Morbi lectus risus, iaculis vel, suscipit quis.
     * %param[default] var1 Lorem ipsum dolor sit amet, consectetur adipiscing elit.
     * %return Tincidunt eget, tempus vel, pede.
     */
    regFunctor<nullptr_t, LoremIpsumOtherType>(p, Lorem::getIpsumAction,
        std::bind(&Lorem::getIpsum, this, _1, _2, _3));
}

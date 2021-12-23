// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

struct StructA
{
    std::vector<StructB> vectorB;
};

struct StructB: StructA
{
    std::vector<StructB> vectorB;
    StructA fieldA;
};

struct StructC: StructB
{
    StructC fieldC;
    StructA fieldA;
};

struct StructD
{
    StructD dInD;
    std::vector<StructD> vectorDinD;
    StructE eInD;
    std::vector<StructE> vectorEInD;
    StructF fInD;
    std::vector<StructF> vectorFInD;
};

struct StructE: StructD
{
    StructD dInE;
    std::vector<StructD> vectorDinE;
    StructE eInE;
    std::vector<StructE> vectorEInE;
    StructF fInE;
    std::vector<StructF> vectorFInE;
};

struct StructF: StructE
{
    StructD dInF;
    std::vector<StructD> vectorDinF;
    StructE eInF;
    std::vector<StructE> vectorEInF;
    StructF fInF;
    std::vector<StructF> vectorFInF;
    std::optional<StructD> optionalDinF;
};
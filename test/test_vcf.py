import os
import subprocess
import genomicsqlite

HERE = os.path.dirname(__file__)
BUILD = os.path.abspath(os.path.join(HERE, "..", "build"))


def vcf_into_sqlite(infilename, outfilename, *options):
    cmd = (
        [os.path.join(BUILD, "loaders/vcf_into_sqlite")] + list(options) + [infilename, outfilename]
    )
    print(" ".join(cmd))
    subprocess.run(
        cmd, check=True,
    )
    print(outfilename)


def test_gnomad_sites_small(tmp_path):
    dbfile = str(tmp_path / "test.gsql")

    vcf_into_sqlite(
        os.path.join(HERE, "data/gnomad.r3.0.sites.ALDH2.vcf.bgz"),
        str(dbfile),
        "--table-prefix",
        "gnomad_",
    )

    con = genomicsqlite.connect(dbfile, read_only=True)
    query = (
        "SELECT gnomad_variants.rowid, id_jsarray FROM (SELECT rid FROM _gri_refseq_meta WHERE name=?) AS chrom,"
        + genomicsqlite.overlapping_genomic_ranges(con, "gnomad_variants", qrid="chrom.rid")
    )
    rs671 = ("chr12", 111803912, 111804012)
    print(query)
    for expl in con.execute("EXPLAIN QUERY PLAN " + query, rs671):
        print(expl[3])
    results = list(con.execute(query, rs671))
    results_rowids = set(vt[0] for vt in results)
    assert next(vt for vt in results if vt[1] and "rs671" in vt[1])

    control = (
        "SELECT gnomad_variants.rowid FROM gnomad_variants WHERE NOT ((pos+rlen) < ? OR pos > ?)"
    )
    control_rowids = set(vt[0] for vt in con.execute(control, (rs671[1], rs671[2])))
    assert len(control_rowids) == 22
    assert results_rowids == control_rowids


def test_gvcf_dv(tmp_path):
    dbfile = str(tmp_path / "test.gsql")
    vcf_into_sqlite(
        os.path.join(HERE, "data/NA12878.dv0.8.0.chr21.g.vcf.gz"),
        str(dbfile),
        "--assembly",
        "GRCh38",
    )
    rows = 962896
    con = genomicsqlite.connect(dbfile, read_only=True)
    assert next(con.execute("SELECT COUNT(*) FROM variants"))[0] == rows
    assert next(con.execute("SELECT COUNT(*) FROM genotypes"))[0] == rows


def test_gvcf_hc(tmp_path):
    dbfile = str(tmp_path / "test.gsql")
    vcf_into_sqlite(
        os.path.join(HERE, "data/hc.NA12878.chr22:25000000-30000000.g.vcf.gz"),
        str(dbfile),
        "--assembly",
        "GRCh38",
    )
    rows = 823480
    con = genomicsqlite.connect(dbfile, read_only=True)
    assert next(con.execute("SELECT COUNT(*) FROM variants"))[0] == rows
    assert next(con.execute("SELECT COUNT(*) FROM genotypes"))[0] == rows


def test_pvcf_glnexus(tmp_path):
    dbfile = str(tmp_path / "test.gsql")
    vcf_into_sqlite(
        os.path.join(HERE, "data/dv_glnexus.1KGP.ALDH2.vcf.gz"),
        str(dbfile),
        "--assembly",
        "GRCh38",
    )
    rows = 1993
    samples = 2504
    con = genomicsqlite.connect(dbfile, read_only=True)
    assert next(con.execute("SELECT COUNT(*) FROM variants")) == (rows,)
    assert next(con.execute("SELECT COUNT(*) FROM genotypes")) == (rows * samples,)
    assert next(con.execute("SELECT SUM(DP) FROM genotypes")) == (134178640,)
    assert round(next(con.execute("SELECT SUM(QUAL) FROM variants"))[0]) == 118146
    assert next(con.execute("SELECT SUM(_gri_bin) FROM variants")) == (545225262781,)
    assert list(
        con.execute(
            "SELECT GT1, GT2, COUNT(*) AS ct FROM genotypes GROUP BY GT1, GT2 ORDER BY ct DESC LIMIT 8"
        )
    ) == [
        (0, 0, 4840519),
        (0, 1, 75297),
        (1, 1, 33338),
        (None, None, 32971),
        (0, 2, 2780),
        (1, 2, 1109),
        (0, 3, 979),
        (2, 2, 554),
    ]
    # ...exercise JSON1 queries


def test_pvcf_gatk(tmp_path):
    dbfile = str(tmp_path / "test.gsql")
    vcf_into_sqlite(
        os.path.join(HERE, "data/gatk.1KGP.ALDH2.vcf.gz"), str(dbfile), "--assembly", "GRCh38",
    )
    rows = 2087
    samples = 2504
    con = genomicsqlite.connect(dbfile, read_only=True)
    assert next(con.execute("SELECT COUNT(*) FROM variants"))[0] == rows
    assert next(con.execute("SELECT COUNT(*) FROM genotypes"))[0] == rows * samples

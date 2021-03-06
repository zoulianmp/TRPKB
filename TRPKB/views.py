import re

from django.http import HttpResponse, Http404
from django.shortcuts import render

from KB_SNP.models import Association
from KB_SNP.models import Tumor, Gene, Variant, EvidenceBasedMedicineLevel, Research, Prognosis, Subgroup

from .importData import read_xls


def get_stats():
    return {'research_num': len(Research.objects.all()),
            'gene_num': len(Gene.objects.all()),
            'variant_num': len(Variant.objects.all()),
            'case_num': len(Association.objects.all()),}


def index(request):
    context = {'stats': get_stats()}
    return render(request, 'index.html', context)


def about_the_knowledgebase(request):
    context = {'stats': get_stats()}
    return render(request, 'index.html', context)


def about_the_knowledge(request):
    context = {'stats': get_stats()}
    return render(request, 'index.html', context)


def access_the_knowledge(request):
    context = {'stats': get_stats()}
    return render(request, 'access_the_knowledge.html', context)


def submit_the_knowledge(request):
    context = {'stats': get_stats()}
    return render(request, 'index.html', context)


def news(request):
    context = {'stats': get_stats()}
    return render(request, 'index.html', context)


def search_snp(request):
    context = {'stats': get_stats(), 'num': None, 'desc': None, 'dt_data': []}
    try:
        term_gene = request.POST['gene']
        term_variant = request.POST['variant']
        term_tumor = request.POST['tumor']

        if term_gene:
            results = Association.objects.filter(
                tumor__name__contains=term_tumor).filter(
                variant__dbsnp__contains=term_variant).filter(
                variant__gene__gene_official_symbol__contains=term_gene)
        else:
            results = Association.objects.filter(
                tumor__name__contains=term_tumor).filter(
                variant__dbsnp__contains=term_variant)

        if len(results) == 0:
            context['num'] = 0
            context['desc'] = ", Please refine your key words."
        else:
            

            row_data = {}
            for i, r in enumerate(results):
                tumor = r.tumor.name
                gene = r.variant.gene.gene_official_symbol if r.variant.gene else ''
                variant = r.variant.dbsnp
                tumor_id = r.tumor.pk
                variant_id = r.variant.pk
                key = "{}-{}-{}".format(tumor, gene, variant)
                if key not in row_data:
                    row_data[key] = {'tumor': tumor, 'tumor_id': tumor_id, 'gene': gene,
                                     'variant': variant, 'variant_id': variant_id, 'research': set()}
                row_data[key]['research'].add((r.research.title, r.research.pk))
            for i, (k, v) in enumerate(row_data.items()):
                research = ""
                for title, pk in v['research']:
                    research += "<p><a href=\"/details_snp/{}/{}/{}\">{}</a></p>".format(pk, v['tumor_id'], v['variant_id'], title)
                row = [i + 1,
                       v['gene'],
                       v['variant'],
                       v['tumor'],
                       research]
                context['dt_data'].append(row)

            context['num'] = len(row_data)
            context['desc'] = ""

    except Exception as e:
        raise e

    return render(request, 'search_results.html', context)


def details_snp(request, research_id, tumor_id, variant_id):
    context = {'stats': get_stats(),
               'research': {}, 'tumor': {}, 'variant': {}, 'gene': {},
               'tabs': {'tab': [], 'content': {}}}

    research = Research.objects.get(pk=research_id)
    context['research'] = {'title': research.title, 'pub_year': research.pub_year,
                           'pubmed_id': research.pubmed_id, 'treatment_type': research.treatment_type,
                           'patient_number': research.patient_number, 'ethnicity': research.ethnicity,
                           'ebml': research.ebml}

    tumor = Tumor.objects.get(pk=tumor_id)
    context['tumor']['name'] = tumor.name

    variant = Variant.objects.get(pk=variant_id)
    context['variant']['dbsnp'] = variant.dbsnp

    gene = variant.gene
    context['gene']['name'] = gene.gene_official_symbol if gene else ''
    context['gene']['full_name'] = gene.gene_official_full_name if gene else ''
    context['gene']['alias'] = ', '.join(gene.gene_alternative_symbols) if (gene and gene.gene_alternative_symbols) else ''
    context['gene']['type'] = gene.gene_type if gene else ''
    context['gene']['summary'] = gene.gene_summary if gene else ''

    association = Association.objects.filter(research__pk=research_id,
                                             tumor__pk=tumor_id,
                                             variant__pk=variant_id)
    prognosis = {}
    for row in association:
        p_id = row.prognosis.pk
        name = row.prognosis.prognosis_name
        if p_id not in prognosis:
            prognosis[p_id] = name
        else:
            continue
    for p_id in prognosis:
        context['tabs']['tab'].append({'p_id': p_id, 'name': prognosis[p_id]})

        subgroups = {}
        a_p = association.filter(prognosis__pk=p_id)
        for row in a_p:
            if row.subgroup:
                subgroup_name = row.subgroup.subgroup
            else:
                subgroup_name = ''
            if subgroup_name not in subgroups:
                subgroups[subgroup_name] = []

            subgroups[subgroup_name].append({
                'genotype': row.genotype,
                'case_number': row.case_number,
                'total_number': row.total_number,
                'hr_u': row.hr_u,
                'ci_u_95': row.ci_u_95,
                'p_u': row.p_u,
                'hr_m': row.hr_m,
                'ci_m_95': row.ci_m_95,
                'p_m': row.p_m,
                })
        context['tabs']['content'][p_id] = subgroups

    return render(request, 'details_snp.html', context)


def import_data(request):
    def get_via_pk(pk, data, i=1):
        for row in data:
            if row[0] == pk:
                return row[i]
        return None

    if 'path' in request.GET and 'table' in request.GET:
        try:
            path = request.GET['path']
            table = request.GET['table']

            data = read_xls(path)
            if re.search('research', table) or re.search('all', table):
                for row in data['research']:
                    EvidenceBasedMedicineLevel.objects.get_or_create(ebml=row[7])
                for row in data['research']:
                    pubmed_id = int(row[4]) if row[4] else None
                    ebml = EvidenceBasedMedicineLevel.objects.get(ebml=row[7])
                    ethnicity = row[8] if row[8] else None
                    male = int(row[10]) if row[10] else None
                    female = int(row[11]) if row[11] else None
                    median_age = float(row[12]) if row[12] else None
                    mean_age = float(row[13]) if row[13] else None
                    age_range = [float(x) for x in row[14].split('-')] if row[14] else None
                    Research.objects.get_or_create(title=row[1], language=row[2], pub_year=int(row[3]),
                        pubmed_id=pubmed_id, url=row[5], pub_type=row[6], ebml=ebml,
                        ethnicity=ethnicity, patient_number=int(row[9]), male=male, female=male,
                        median_age=median_age, mean_age=mean_age,
                        age_range=age_range)
            if re.search('tumor', table) or re.search('all', table):
                for row in data['tumor']:
                    Tumor.objects.get_or_create(name=row[1])
            if re.search('gene', table) or re.search('all', table):
                for row in data['gene']:
                    Gene.objects.get_or_create(gene_official_symbol=row[1], entrez_gene_id=int(row[2]))
            if re.search('variant', table) or re.search('all', table):
                for row in data['variant']:
                    gene = Gene.objects.get(gene_official_symbol=get_via_pk(row[1], data['gene'])) if row[1] else None
                    Variant.objects.get_or_create(gene=gene, dbsnp=row[2])
            if re.search('prognosis', table) or re.search('all', table):
                for row in data['prognosis']:
                    prognosis_type = row[2] if row[2] else None
                    endpoint = row[3] if row[3] else None
                    case_meaning = row[5] if row[5] else None
                    control_meaning = row[6] if row[6] else None
                    total_meaning = row[7] if row[7] else None
                    annotation = row[9] if row[9] else None
                    Prognosis.objects.create(prognosis_name=row[1], prognosis_type=prognosis_type,
                        endpoint=endpoint, original=row[4], case_meaning=case_meaning, control_meaning=control_meaning,
                        total_meaning=total_meaning, annotation=annotation)
            if re.search('subgroup', table) or re.search('all', table):
                for row in data['subgroup']:
                    prognosis = Prognosis.objects.get(pk=int(row[1]))
                    Subgroup.objects.get_or_create(prognosis=prognosis, subgroup=row[2])
            if re.search('association', table) or re.search('all', table):
                for row in data['association']:
                    research = Research.objects.get(title=get_via_pk(row[1], data['research']))
                    tumor = Tumor.objects.get(name=get_via_pk(row[2], data['tumor']))
                    variant = Variant.objects.get(dbsnp=get_via_pk(row[4], data['variant'], 2))
                    prognosis = Prognosis.objects.get(pk=int(row[5]))
                    subgroup = Subgroup.objects.get(pk=int(row[6])) if row[6] else None
                    case_number = int(row[8]) if row[8] else None
                    control_number = int(row[9]) if row[9] else None
                    total_number = int(row[10]) if row[10] else None
                    or_u = float(row[11]) if row[11] else None
                    hr_u = float(row[12]) if row[12] else None
                    rr_u = float(row[13]) if row[13] else None
                    ci_u_95 = [float(x) for x in row[14].split('-')] if row[14] else None
                    p_u = row[15] if row[15] else None
                    or_m = float(row[16]) if row[16] else None
                    hr_m = float(row[17]) if row[17] else None
                    rr_m = float(row[18]) if row[18] else None
                    i_m_95 = [float(x) for x in row[19].split('-')] if row[19] else None
                    p_m = row[20] if row[20] else None
                    Association.objects.get_or_create(research=research, tumor=tumor, variant=variant,
                        prognosis=prognosis, subgroup=subgroup, genotype=row[7], case_number=case_number,
                        control_number=control_number, total_number=total_number, or_u=or_u, hr_u=hr_u,
                        rr_u=rr_u, ci_u_95=ci_u_95, p_u=p_u, or_m=or_m, hr_m=hr_m, rr_m=rr_m, i_m_95=i_m_95, p_m=p_m)
        except Exception as e:
            raise e

        return HttpResponse("OK!")
    else:
        return render(request, 'import_data.html')

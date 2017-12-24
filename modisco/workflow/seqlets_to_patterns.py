from .. import nearest_neighbors


class TfModiscoSeqletsToPatternsFactory(AbstractSeqletsToPatterns):

    def __init__(self, n_cores=20,
                       min_overlap_while_sliding=0.7,

                       #gapped kmer embedding arguments
                       alphabet_size=4,
                       kmer_len=8, num_gaps=3, num_mismatches=2,
                       gpu_batch_size=200,

                       nn_n_jobs=4,
                       nearest_neighbors_to_compute=500,

                       affmat_correlation_threshold=0.15,

                       tsne_perplexity = 10,
                       louvain_num_runs_and_levels_r1=[(50,-1)],
                       louvain_num_runs_and_levels_r2=[(200,-1)],
                       louvain_contin_runs_r1 = 20,
                       louvain_contin_runs_r2 = 50,
                       final_louvain_level_to_return=1,

                       frac_support_to_trim_to=0.2,
                       trim_to_window_size=30,
                       initial_flank_to_add=10,

                       prob_and_pertrack_sim_merge_thresholds=[
                        (0.0001,0.84), (0.00001, 0.87), (0.000001, 0.9)],

                       prob_and_pertrack_sim_dealbreaker_thresholds=[
                        (0.1,0.75), (0.01, 0.8), (0.001, 0.83),
                        (0.0000001,0.9)],

                       min_similarity_for_seqlet_assignment=0.2,
                       final_min_cluster_size=30,

                       final_flank_to_add=10,
                       verbose=True,
                       batch_size=50):

        #affinity_mat calculation
        self.n_cores = n_cores
        self.min_overlap_while_sliding = min_overlap_while_sliding

        #gapped kmer embedding arguments
        self.alphabet_size = alphabet_size
        self.kmer_len = kmer_len
        self.num_gaps = num_gaps
        self.num_mismatches = num_mismatches
        self.gpu_batch_size = gpu_batch_size

        self.nn_n_jobs = nn_n_jobs
        self.nearest_neighbors_to_compute = nearest_neighbors_to_compute

        self.affmat_correlation_threshold = affmat_correlation_threshold

        #affinity mat to tsne dist mat setting
        self.tsne_perplexity = tsne_perplexity

        #clustering settings
        self.louvain_num_runs_and_levels_r1 = louvain_num_runs_and_levels_r1
        self.louvain_num_runs_and_levels_r2 = louvain_num_runs_and_levels_r2
        self.louvain_contin_runs_r1 = louvain_contin_runs_r1
        self.louvain_contin_runs_r2 = louvain_contin_runs_r2
        self.final_louvain_level_to_return = final_louvain_level_to_return

        #postprocessor1 settings
        self.frac_support_to_trim_to = frac_support_to_trim_to
        self.trim_to_window_size = trim_to_window_size
        self.initial_flank_to_add = initial_flank_to_add 

        #similarity settings for merging
        self.prob_and_pertrack_sim_merge_thresholds =\
            prob_and_pertrack_sim_merge_thresholds
        self.prob_and_sim_merge_thresholds =\
            [(x[0], x[1]*(len(contrib_scores_track_names)
                          +len(hypothetical_contribs_track_names)
                          +len(other_comparison_track_names))
             for x in prob_and_pertrack_sim_merge_thresholds]
        self.prob_and_pertrack_sim_dealbreaker_thresholds =\
            prob_and_pertrack_sim_dealbreaker_thresholds
        self.prob_and_sim_dealbreaker_thresholds =\
            [(x[0], x[1]*(len(contrib_scores_track_names)
                          +len(hypothetical_contribs_track_names)
                          +len(other_comparison_track_names)))
             for x in prob_and_pertrack_sim_dealbreaker_thresholds]

        #reassignment settings
        self.min_similarity_for_seqlet_assignment =\
            min_similarity_for_seqlet_assignment
        self.final_min_cluster_size = final_min_cluster_size

        #final postprocessor settings
        self.final_flank_to_add=final_flank_to_add

        #other settings
        self.verbose = verbose
        self.batch_size = batch_size

    def get_jsonable_config(self):
        to_return =  OrderedDict([
                ('class_name', type(self).__name__),
                ('n_cores', self.n_cores),
                ('min_overlap_while_sliding', self.min_overlap_while_sliding),
                ('alphabet_size', self.alphabet_size),
                ('kmer_len', self.kmer_len),
                ('num_gaps', self.num_gaps),
                ('num_mismatches', self.num_mismatches),
                ('nn_n_jobs', self.nn_n_jobs),
                ('nearest_neighbors_to_compute',
                 self.nearest_neighbors_to_compute),
                ('affmat_correlation_threshold',
                 self.affmat_correlation_threshold),
                ('tsne_perplexity', self.tsne_perplexity),
                ('louvain_num_runs_and_levels_r1',
                 self.louvain_num_runs_and_levels_r1),
                ('louvain_num_runs_and_levels_r2',
                 self.louvain_num_runs_and_levels_r2),
                ('final_louvain_level_to_return',
                 self.final_louvain_level_to_return),
                ('louvain_contin_runs_r1',
                 self.louvain_contin_runs_r1),
                ('louvain_contin_runs_r2',
                 self.louvain_contin_runs_r2),
                ('frac_support_to_trim_to', self.frac_support_to_trim_to),
                ('trim_to_window_size', self.trim_to_window_size),
                ('initial_flank_to_add', self.initial_flank_to_add),
                ('prob_and_pertrack_sim_merge_thresholds',
                 self.prob_and_pertrack_sim_merge_thresholds),
                ('prob_and_pertrack_sim_dealbreaker_thresholds',
                 self.prob_and_pertrack_sim_dealbreaker_thresholds),
                ('min_similarity_for_seqlet_assignment',
                 self.min_similarity_for_seqlet_assignment),
                ('final_min_cluster_size', self.final_min_cluster_size),
                ('final_flank_to_add', self.final_flank_to_add),
                ('batch_size', self.batch_size)]) 
        return to_return

    def __call__(self, track_set, onehot_track_name,
                       contrib_scores_track_names,
                       hypothetical_contribs_track_names,
                       track_signs,
                       other_comparison_track_names):

        assert len(track_signs)==len(hypothetical_contribs_track_names)
        assert len(track_signs)==len(contrib_scores_track_names)

        pattern_comparison_settings =\
            affmat.core.PatternComparisonSettings(
                track_names=hypothetical_contribs_track_names
                            +contrib_scores_track_names
                            +other_comparison_track_names, 
                track_transformer=affmat.L1Normalizer(), 
                min_overlap=self.min_overlap_while_sliding)

        #gapped kmer embedder
        gkmer_embedder = affmat.core.GappedKmerEmbedder(
            alphabet_size=self.alphabet_size,
            kmer_len=self.kmer_len,
            num_gaps=self.num_gaps,
            num_mismatches=self.num_mismatches,
            batch_size=self.gpu_batch_size,
            num_filters_to_retain=None,
            onehot_track_name=onehot_track_name,
            toscore_track_names_and_signs=list(
                zip(hypothetical_contribs_track_names,
                    [np.sign(x) for x in track_signs])),
            normalizer=affmat.core.MeanNormalizer())

        #affinity matrix from embeddings
        coarse_affmat_computer =\
            affmat.core.AffmatFromSeqletEmbeddings(
                seqlets_to_1d_embedder=gkmer_embedder,
                affinity_mat_from_1d=\
                    affmat.core.NumpyCosineSimilarity(
                        verbose=self.verbose,
                        gpu_batch_size=self.gpu_batch_size),
                verbose=self.verbose)

        nearest_neighbors_computer = nearest_neighbors.ScikitNearestNeighbors(
            n_neighbors=self.nearest_neighbors_to_compute,
            nn_n_jobs=self.nn_n_jobs)  

        affmat_from_seqlets_with_nn_pairs =\
            affmat.core.AffmatFromSeqletsWithNNpairs(
                pattern_comparison_settings=pattern_comparison_settings,
                sim_metric_on_nn_pairs=\
                    affmat.core.ParallelCpuCrossMetricOnNNpairs(
                        n_cores=self.n_cores,
                        cross_metric_single_region=
                            affmat.core.CrossContinJaccardSingleRegion()))

        filter_mask_from_correlation =\
            affmat.core.FilterMaskFromCorrelation(
                correlation_threshold=self.affmat_correlation_threshold,
                verbose=self.verbose)

        aff_to_dist_mat = affmat.transformers.AffToDistViaInvLogistic() 
        density_adapted_affmat_transformer =\
            affmat.transformers.TsneConditionalProbs(
                perplexity=tsne_perplexity,
                aff_to_dist_mat=aff_to_dist_mat)

        #prepare the clusterers for the different rounds
        affmat_transformer_r1 = affmat.transformers.SymmetrizeByAddition(
                                probability_normalize=True)
        for n_runs, level_to_return in self.louvain_num_runs_and_levels_r1:
            affmat_transformer_r1 = affmat_transformer_r1.chain(
                affmat.transformers.LouvainMembershipAverage(
                    n_runs=n_runs,
                    level_to_return=level_to_return,
                    parallel_threads=self.n_cores))
        clusterer_r1 = cluster.core.LouvainCluster(
            level_to_return=self.final_louvain_level_to_return,
            affmat_transformer=affmat_transformer_r1,
            contin_runs=self.louvain_contin_runs_r1,
            verbose=self.verbose)

        affmat_transformer_r2 = affmat.transformers.SymmetrizeByAddition(
                                probability_normalize=True)
        for n_runs, level_to_return in self.louvain_num_runs_and_levels_r2:
            affmat_transformer_r2 = affmat_transformer_r2.chain(
                affmat.transformers.LouvainMembershipAverage(
                    n_runs=n_runs,
                    level_to_return=level_to_return,
                    parallel_threads=self.n_cores))
        clusterer_r2 = cluster.core.LouvainCluster(
            level_to_return=self.final_louvain_level_to_return,
            affmat_transformer=affmat_transformer_r2,
            contin_runs=self.louvain_contin_runs_r2,
            verbose=self.verbose)
        
        clusterer_per_round = [clusterer_r1, clusterer_r2]

        #prepare the seqlet aggregator
        expand_trim_expand1 =\
            aggregator.ExpandSeqletsToFillPattern(
                track_set=track_set,
                flank_to_add=self.initial_flank_to_add).chain(
            aggregator.TrimToBestWindow(
                window_size=self.trim_to_window_size,
                track_names=contrib_scores_track_names)).chain(
            aggregator.ExpandSeqletsToFillPattern(
                track_set=track_set,
                flank_to_add=self.initial_flank_to_add))
        postprocessor1 =\
            aggregator.TrimToFracSupport(
                        frac=self.frac_support_to_trim_to)\
                      .chain(expand_trim_expand1)
        seqlet_aggregator = aggregator.GreedySeqletAggregator(
            pattern_aligner=core.CrossContinJaccardPatternAligner(
                pattern_comparison_settings=pattern_comparison_settings),
                seqlet_sort_metric=
                    lambda x: -sum([np.sum(np.abs(x[track_name].fwd)) for
                               track_name in contrib_scores_track_names]),
            postprocessor=postprocessor1)

        #prepare the similar patterns collapser
        pattern_to_pattern_sim_computer =\
            affmat.core.AffmatFromSeqletsWithNNpairs(
                pattern_comparison_settings=pattern_comparison_settings,
                sim_metric_on_nn_pairs=\
                    affmat.core.ParallelCpuCrossMetricOnNNpairs(
                        n_cores=self.n_cores,
                        cross_metric_single_region=\
                            affmat.core.CrossContinJaccardSingleRegion(),
                        verbose=False))
        similar_patterns_collapser =\
            aggregator.DynamicDistanceSimilarPatternsCollapser(
                pattern_to_pattern_sim_computer=
                    pattern_to_pattern_sim_computer,
                aff_to_dist_mat=aff_to_dist_mat,
                pattern_aligner=core.CrossCorrelationPatternAligner(
                    pattern_comparison_settings=
                        affmat.core.PatternComparisonSettings(
                            track_names=(
                                hypothetical_contribs_track_names+
                                contrib_scores_track_names+
                                other_comparison_track_names), 
                            track_transformer=affmat.MeanNormalizer().chain(
                                              affmat.MagnitudeNormalizer()), 
                            min_overlap=self.min_overlap_while_sliding)),
                collapse_condition=(lambda dist_prob, aligner_sim:
                    any([(dist_prob > x[0] and aligner_sim > x[1])
                         for x in self.prob_and_sim_merge_thresholds])),
                dealbreaker_condition=(lambda dist_prob, aligner_sim:
                    any([(dist_prob < x[0] and aligner_sim < x[1])              
                         for x in self.prob_and_sim_dealbreaker_thresholds])),
                postprocessor=postprocessor1,
                verbose=self.verbose) 

        seqlet_reassigner =\
           aggregator.ReassignSeqletsFromSmallClusters(
            seqlet_assigner=aggregator.AssignSeqletsByBestMetric(
                pattern_comparison_settings=pattern_comparison_settings,
                individual_aligner_metric=
                    core.get_best_alignment_crosscontinjaccard,
                matrix_affinity_metric=
                    affmat.core.CrossContinJaccardMultiCoreCPU(
                        verbose=self.verbose, n_cores=self.n_cores),
                min_similarity=self.min_similarity_for_seqlet_assignment),
            min_cluster_size=self.final_min_cluster_size,
            postprocessor=self.expand_trim_expand1,
            verbose=self.verbose) 

        final_postprocessor = aggregator.ExpandSeqletsToFillPattern(
                                        track_set=track_set,
                                        flank_to_add=self.final_flank_to_add) 

        return TfModiscoSeqletsToPatterns(
                coarse_affmat_computer=coarse_affmat_computer,
                nearest_neighbors_computer=nearest_neighbors_computer,
                affmat_from_seqlets_with_nn_pairs=
                    affmat_from_seqlets_with_nn_pairs, 
                filter_mask_from_correlation=filter_mask_from_correlation,
                density_adapted_affmat_transformer=
                    density_adapted_affmat_transformer,
                clusterer_per_round=clusterer_per_round,
                seqlet_aggregator=seqlet_aggregator,
                similar_patterns_collapser=similar_patterns_collapser,
                seqlet_reassigner=seqlet_reassigner,
                final_postprocessor=final_postprocessor,
                verbose=self.verbose)

    def save_hdf5(self, grp):
        grp.attrs['jsonable_config'] =\
            json.dumps(self.jsonable_config, indent=4, separators=(',', ': ')) 


class SeqletsToPatternsResults(object):

    def __init__(self,
                 patterns, seqlets, affmat, cluster_results,
                 total_time_taken,
                 jsonable_config, **kwargs):
        self.patterns = patterns
        self.seqlets = seqlets
        self.affmat = affmat
        self.cluster_results = cluster_results
        self.total_time_taken = total_time_taken
        self.__dict__.update(**kwargs)

    def save_hdf5(self, grp):
        util.save_patterns(grp.create_group("patterns"))
        grp.create_dataset("affmat", data=self.affmat) 
        grp.create_dataset("cluster_results", data=self.cluster_results)   
        #grp.attrs['jsonable_config'] =\
        #    json.dumps(self.jsonable_config, indent=4, separators=(',', ': ')) 
        grp.attrs['total_time_taken'] = self.total_time_taken


class TfModiscoSeqletsToPatterns(AbstractSeqletsToPatterns):

    def __init__(self, coarse_affmat_computer,
                       nearest_neighbors_computer,
                       affmat_from_seqlets_with_nn_pairs, 
                       filter_mask_from_correlation,
                       density_adapted_affmat_transformer,
                       clusterer_per_round,
                       seqlet_aggregator,
                       similar_patterns_collapser,
                       seqlet_reassigner,
                       final_postprocessor,
                       verbose=True):

        self.coarse_affmat_computer = coarse_affmat_computer
        self.nearest_neighbors_computer = nearest_neighbors_computer
        self.affmat_from_seqlets_with_nn_pairs =\
            affmat_from_seqlets_with_nn_pairs
        self.filter_mask_from_correlation = filter_mask_from_correlation
        self.density_adapted_affmat_transformer =\
            density_adapted_affmat_transformer
        self.clusterer_per_round = clusterer_per_round 
        self.seqlet_aggregator = seqlet_aggregator
        
        self.similar_patterns_collapser = similar_patterns_collapser
        self.seqlet_reassigner = seqlet_reassigner
        self.final_postprocessor = final_postprocessor

        self.verbose = verbose


    def __call__(self, seqlets):

        start = time.time()

        for round_num, clusterer in enumerate(self.clusterer_per_round)):

            if (self.verbose):
                print("(Round "+str(round_num)+") Computing coarse affmat")
                sys.stdout.flush()
            coarse_affmat = self.coarse_affmat_computer(seqlets)

            nn_start = time.time() 
            if (self.verbose):
                print("(Round "+str(round_num)+") Compute nearest neighbors"
                      +"from coarse affmat")
                sys.stdout.flush()

            seqlet_neighbors = self.nearest_neighbors_computer(coarse_affmat)

            if (self.verbose):
                print("Computed nearest neighbors in",
                      round(time.time()-nn_start1,2),"s")
                sys.stdout.flush()

            nn_affmat_start = time.time() 
            if (self.verbose):
                print("(Round "+str(round_num)+") Computing affinity matrix"
                      +" on nearest neighbors")
                sys.stdout.flush()
            nn_affmat = self.affmat_from_seqlets_with_nn_pairs(
                                        seqlet_neighbors=seqlet_neighbors,
                                        seqlets=seqlets) 
            if (self.verbose):
                print("(Round "+str(round_num)+") Computed affinity matrix"
                      +" on nearest neighbors in",
                      round(time.time()-nn_affmat_start,2),"s")
                sys.stdout.flush()

            #filter by correlation
            filtered_rows_mask = self.filter_mask_from_correlation(
                                    main_affmat=nn_affmat,
                                    other_affmat=coarse_affmat) 
            filtered_seqlets = [x[0] for x in
                       zip(seqlets, filtered_rows_mask) if (x[1])]
            filtered_affmat =\
                nn_affmat[filtered_rows_mask][:,filtered_rows_mask]

            if (self.verbose):
                print("(Round "+str(round_num)+") Retained "
                      +str(np.sum(filtered_rows_mask))
                      +" rows out of "+str(len(filtered_rows_mask))
                      +" after filtering")
                sys.stdout.flush()

            if (self.verbose):
                print("(Round "+str(round_num)+") Computing density "
                      +"adapted affmat")
                sys.stdout.flush() 

            density_adapted_affmat =\
                self.density_adapted_affmat_transformer(filtered_affmat)

            if (self.verbose):
                print("(Round "+str(round_num)+") Computing clustering")
                sys.stdout.flush() 

            cluster_results = clusterer(density_adapted_affmat)
            num_clusters = max(cluster_results.cluster_indices+1)
            cluster_idx_counts = Counter(cluster_results.cluster_indices)
            if (self.verbose):
                print("Got "+str(num_clusters)
                      +" clusters after round "+str(round_num))
                print("Counts:")
                print(dict([x for x in cluster_idx_counts.items()]))
                sys.stdout.flush()

            if (self.verbose):
                print("(Round "+str(round_num)+") Aggregating seqlets"
                      +" in each cluster")
                sys.stdout.flush()

            cluster_to_seqlets = defaultdict(list) 
            assert len(filtered_seqlets)==len(cluster_results.cluster_indices)
            for seqlet,idx in zip(filtered_seqlets,
                                  cluster_results.cluster_indices):
                cluster_to_seqlets[idx].append(seqlet)

            cluster_to_eliminated_motif = OrderedDict()
            cluster_to_motif = OrderedDict()
            for i in range(num_clusters):
                if (self.verbose):
                    print("Aggregating for cluster "+str(i)+" with "
                          +str(len(cluster_to_seqlets[i]))+" seqlets")
                    sys.stdout.flush()
                motifs = self.seqlet_aggregator(cluster_to_seqlets[i])
                assert len(motifs)==1
                motif = motifs[0]
                motif_track_signs = [
                    np.sign(np.sum(motif[contrib_scores_track_name].fwd)) for
                    contrib_scores_track_name in contrib_scores_track_names] 
                if (all([(x==y) for x,y in
                        zip(motif_track_signs, track_signs)])):
                    cluster_to_motif[i] = motif
                else:
                    if (self.verbose):
                        print("Dropping cluster "+str(i)+
                              " with "+str(motif.num_seqlets)
                              +" seqlets due to sign disagreement")
                    cluster_to_eliminated_motif[i] = motif

            #obtain unique seqlets from adjusted motifs
            seqlets = dict([(y.exidx_start_end_string, y)
                             for x in cluster_to_motif.values()
                             for y in x.seqlets]).values()

        #Now start merging patterns 
        if (self.verbose):
            print("Merging clusters")
            sys.stdout.flush()
        merged_patterns, pattern_merge_hierarchy =\
            self.similar_patterns_collapser( 
                patterns=cluster_to_motif.values(), seqlets=seqlets) 
        merged_patterns = sorted(merged_patterns, key=lambda x: -x.num_seqlets)
        if (self.verbose):
            print("Got "+str(len(merged_patterns))+" patterns after merging")
            sys.stdout.flush()

        if (self.verbose):
            print("Performing seqlet reassignment")
            sys.stdout.flush()
        reassigned_patterns = self.seqlet_reassigner(merged_patterns)
        final_patterns = self.final_postprocessor(reassigned_patterns)
        if (self.verbose):
            print("Got "+str(len(final_patterns))
                  +" patterns after reassignment")
            sys.stdout.flush()

        total_time_taken = round(time.time()-start,2)
        if (self.verbose):
            print("Total time taken is "
                  +str(total_time_taken)+"s")
            sys.stdout.flush()

        results = SeqletsToPatternsResults(
            patterns=final_patterns,
            seqlets=filtered_seqlets, #last stage of filtered seqlets
            affmat=filtered_affmat,
            cluster_results=cluster_results, 
            total_time_taken=total_time_taken)

        return results 


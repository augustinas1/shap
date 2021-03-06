import numpy as np
try:
    import matplotlib.pyplot as pl
    import matplotlib
except ImportError:
    pass
from . import labels
from . import colors

# TODO: remove color argument / use color argument
def dependence_plot(ind, shap_values, features, feature_names=None, display_features=None,
                    interaction_index="auto", color="#1E88E5", axis_color="#333333",
                    dot_size=16, alpha=1, title=None, show=True, num_plots=1, filename=None):
    """
    Create a SHAP dependence plot, colored by an interaction feature.

    Parameters
    ----------
    ind : int
        Index of the feature to plot.

    shap_values : numpy.array
        Matrix of SHAP values (# samples x # features)

    features : numpy.array or pandas.DataFrame
        Matrix of feature values (# samples x # features)

    feature_names : list
        Names of the features (length # features)

    display_features : numpy.array or pandas.DataFrame
        Matrix of feature values for visual display (such as strings instead of coded values)

    interaction_index : "auto", None, or int
        The index of the feature used to color the plot.

    num_plots : int
        Number of dependence plots to be created allowing to see dependencies on more than
        one most correlated feature.

        If set to 1 maintain default functionality.
    """

    # convert from DataFrames if we got any
    if str(type(features)).endswith("'pandas.core.frame.DataFrame'>"):
        if feature_names is None:
            feature_names = features.columns
        features = features.values
    if str(type(display_features)).endswith("'pandas.core.frame.DataFrame'>"):
        if feature_names is None:
            feature_names = display_features.columns
        display_features = display_features.values
    elif display_features is None:
        display_features = features

    if feature_names is None:
        feature_names = [labels['FEATURE'] % str(i) for i in range(shap_values.shape[1])]

    # allow vectors to be passed
    if len(shap_values.shape) == 1:
        shap_values = np.reshape(shap_values, len(shap_values), 1)
    if len(features.shape) == 1:
        features = np.reshape(features, len(features), 1)

    def convert_name(ind):
        if type(ind) == str:
            nzinds = np.where(feature_names == ind)[0]
            if len(nzinds) == 0:
                print("Could not find feature named: " + ind)
                return None
            else:
                return nzinds[0]
        else:
            return ind

    ind = convert_name(ind)

    interaction_plot = False
    interactions_sorted = None

    # plotting SHAP interaction values
    if len(shap_values.shape) == 3 and len(ind) == 2:

        ind = convert_name(ind[0])

        interaction_plot = True

        interactions = np.abs(shap_values[:, ind, :]).sum(0)
        interactions_sorted = np.argsort(-interactions)
        interaction_index = interactions_sorted[0]

        # put the main effect as the first element for the sake of clarity
        if (interaction_index != ind):
            interaction_index = np.where(interactions_sorted == ind)
            interactions_sorted = np.delete(interactions_sorted, interaction_index)
            interactions_sorted = np.insert(interactions_sorted, 0, ind)

        ylim_max = np.amax(shap_values[:, ind, interactions_sorted[:num_plots]])*2
        ylim_min = np.amin(shap_values[:, ind, interactions_sorted[:num_plots]])*2
        print(ylim_max, ylim_min)


    # plotting dependence values

    # guess what other feature as the strongest interaction with the plotted feature
    if interaction_index == "auto":
        interactions = approx_interactions(ind, shap_values, features)
        interactions_sorted = np.argsort(-np.abs(interactions))
        interaction_index = interactions_sorted[0]
        #print (interactions_sorted)
        #print (feature_names[interactions_sorted])

    # Need to initialise this, otherwise breaks
    if (interactions_sorted is None):
        interactions_sorted = np.array((1, ))
        print(interaction_index)
        interactions_sorted.fill(interaction_index)

    # Create a figure for all the subplots
    cols = 1
    rows = num_plots // cols
    rows += num_plots % cols
    position = range(1, num_plots+1)
    fig_width = 7.5 * cols
    fig_height = 5 * rows
    fig = pl.figure(1, figsize=(fig_width, fig_height))

    # Create actual plots
    for i in range(num_plots):
        ax = fig.add_subplot(rows, cols, position[i])

        # allow a single feature name to be passed alone
        if type(feature_names) == str:
            feature_names = [feature_names]
        name = feature_names[ind]

        interaction_index = interactions_sorted[i]
        print(interactions[interaction_index], feature_names[interaction_index])
        interaction_index = convert_name(interaction_index)

        if interaction_plot:

            if ind == interaction_index:
                proj_shap_values = shap_values[:, interaction_index, :]
            else:
                proj_shap_values = shap_values[:, interaction_index, :] * 2  # off-diag values are split in half

            plot_the_plot(ax, ind, proj_shap_values, features,
                          feature_names, display_features,
                          interaction_index, color, axis_color,
                          dot_size, alpha, title, show=False)

            if ind == interaction_index:
                ax.set_ylabel(labels['MAIN_EFFECT'] % feature_names[ind], fontsize=11)
            else:
                ax.set_ylabel(labels['INTERACTION_EFFECT'] % (feature_names[ind], feature_names[interaction_index]), fontsize=11)

            # Normalise the plot y-axis values
            ax.set_ylim(ylim_min-0.02, ylim_max+0.02)

        else:

            plot_the_plot(ax, ind, shap_values, features,
                          feature_names, display_features,
                          interaction_index, color, axis_color,
                          dot_size, alpha, title, show=False)

            if (i % cols == 0):
                ax.set_ylabel(labels['VALUE_FOR'] % name, color=axis_color, fontsize=13)

        if (i+1 > num_plots-cols):
            ax.set_xlabel(name, color=axis_color, fontsize=13)

    if title is not None:
        fig.set_title(title, color=axis_color, fontsize=13)

    if filename is not None:
        pl.tight_layout()
        pl.savefig(filename, dpi=150)
    if show:
        pl.show()

def plot_the_plot(ax, ind, shap_values, features,
                  feature_names=None, display_features=None,
                  interaction_index=None, color="#1E88E5", axis_color="#333333",
                  dot_size=16, alpha=1, title=None, show=False):

    assert shap_values.shape[0] == features.shape[0], \
        "'shap_values' and 'features' values must have the same number of rows!"
    assert shap_values.shape[1] == features.shape[1], \
        "'shap_values' must have the same number of columns as 'features'!"

    # get both the raw and display feature values
    xv = features[:, ind]
    xd = display_features[:, ind]
    s = shap_values[:, ind]
    if type(xd[0]) == str:
        name_map = {}
        for i in range(len(xv)):
            name_map[xd[i]] = xv[i]
        xnames = list(name_map.keys())

    categorical_interaction = False
    # get both the raw and display color values
    if interaction_index is not None:
        cv = features[:, interaction_index]
        cd = display_features[:, interaction_index]
        clow = np.nanpercentile(features[:, interaction_index].astype(np.float), 5)
        chigh = np.nanpercentile(features[:, interaction_index].astype(np.float), 95)
        if type(cd[0]) == str:
            cname_map = {}
            for i in range(len(cv)):
                cname_map[cd[i]] = cv[i]
            cnames = list(cname_map.keys())
            categorical_interaction = True
        elif clow % 1 == 0 and chigh % 1 == 0 and len(set(features[:, interaction_index])) < 50:
            categorical_interaction = True

    # discretize colors for categorical features
    color_norm = None
    if categorical_interaction and clow != chigh:
        bounds = np.linspace(clow, chigh, chigh - clow + 2)
        color_norm = matplotlib.colors.BoundaryNorm(bounds, colors.red_blue.N)

    # the actual scatter plot, TODO: adapt the dot_size to the number of data points?
    if interaction_index is not None:
        plot_ax = ax.scatter(xv, s, s=dot_size, linewidth=0, c=features[:, interaction_index], cmap=colors.red_blue,
                   alpha=alpha, vmin=clow, vmax=chigh, norm=color_norm, rasterized=len(xv) > 500)
    else:
        plot_ax = ax.scatter(xv, s, s=dot_size, linewidth=0, color="#1E88E5",
                   alpha=alpha, rasterized=len(xv) > 500)

    if interaction_index != ind and interaction_index is not None:
        # draw the color bar
        if type(cd[0]) == str:
            tick_positions = [cname_map[n] for n in cnames]
            if len(tick_positions) == 2:
                tick_positions[0] -= 0.25
                tick_positions[1] += 0.25
            cb = pl.colorbar(plot_ax, ax=ax, ticks=tick_positions)
            cb.set_ticklabels(ax, cnames)
        else:
            cb = pl.colorbar(plot_ax, ax=ax)

        cb.set_label(feature_names[interaction_index], size=13)
        cb.ax.tick_params(labelsize=11)
        if categorical_interaction:
            cb.ax.tick_params(length=0)
        cb.set_alpha(1)
        cb.outline.set_visible(False)
        bbox = cb.ax.get_window_extent().transformed(pl.gcf().dpi_scale_trans.inverted())
        cb.ax.set_aspect((bbox.height - 0.7) * 20)

    ax.xaxis.set_ticks_position('bottom')
    ax.yaxis.set_ticks_position('left')
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.tick_params(color=axis_color, labelcolor=axis_color, labelsize=11)
    for spine in ax.spines.values():
        spine.set_edgecolor(axis_color)
    if type(xd[0]) == str:
        ax.set_xticks([name_map[n] for n in xnames], xnames, rotation='vertical', fontsize=11)


def approx_interactions(index, shap_values, X):
    """ Order other features by how much interaction they seem to have with the feature at the given index.

    This just bins the SHAP values for a feature along that feature's value. For true Shapley interaction
    index values for SHAP see the interaction_contribs option implemented in XGBoost.
    """

    if X.shape[0] > 10000:
        a = np.arange(X.shape[0])
        np.random.shuffle(a)
        inds = a[:10000]
    else:
        inds = np.arange(X.shape[0])

    x = X[inds, index]
    srt = np.argsort(x)
    shap_ref = shap_values[inds, index]
    shap_ref = shap_ref[srt]
    inc = max(min(int(len(x) / 10.0), 50), 1)
    interactions = []
    for i in range(X.shape[1]):
        val_other = X[inds, i][srt].astype(np.float)
        v = 0.0
        if not (i == index or np.sum(np.abs(val_other)) < 1e-8):
            for j in range(0, len(x), inc):
                if np.std(val_other[j:j + inc]) > 0 and np.std(shap_ref[j:j + inc]) > 0:
                    v += abs(np.corrcoef(shap_ref[j:j + inc], val_other[j:j + inc])[0, 1])
        interactions.append(v)

    return interactions

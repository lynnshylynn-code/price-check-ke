package ke.pricecheck.app.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.ContextMenu
import android.view.Menu
import android.view.MenuInflater
import android.view.MenuItem
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.widget.Toolbar
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.updatePadding
import androidx.core.view.MenuProvider
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import ke.pricecheck.app.PriceCheckApplication
import ke.pricecheck.app.R
import ke.pricecheck.app.data.Product
import kotlinx.coroutines.launch

class WatchlistFragment : Fragment() {
    private var gridLayout = false
    private var contextProduct: Product? = null
    private val viewModel: PriceCheckViewModel by activityViewModels {
        PriceCheckViewModel.Factory(
            (requireActivity().application as PriceCheckApplication).container,
        )
    }
    private lateinit var adapter: WatchlistAdapter
    private lateinit var toolbar: Toolbar
    private lateinit var recyclerView: RecyclerView
    private lateinit var emptyState: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        gridLayout = savedInstanceState?.getBoolean(STATE_GRID_LAYOUT) ?: false
    }

    override fun onSaveInstanceState(outState: Bundle) {
        outState.putBoolean(STATE_GRID_LAYOUT, gridLayout)
        super.onSaveInstanceState(outState)
    }

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?,
    ): View {
        adapter = WatchlistAdapter(
            onAddToBasket = { product -> viewModel.changeBasket(product.id, 1) },
            onRemoveFromWatchlist = { product -> viewModel.toggleWatched(product.id) },
            onContextMenu = { anchor, product ->
                contextProduct = product
                registerForContextMenu(anchor)
                anchor.showContextMenu()
            },
        )
        toolbar = Toolbar(requireContext()).apply {
            title = getString(R.string.watchlist_title)
            setNavigationIcon(android.R.drawable.ic_menu_revert)
            setNavigationContentDescription(R.string.navigate_back)
            setNavigationOnClickListener { parentFragmentManager.popBackStack() }
        }
        recyclerView = RecyclerView(requireContext()).apply {
            layoutManager = if (gridLayout) GridLayoutManager(requireContext(), 2)
                else LinearLayoutManager(requireContext())
            adapter = this@WatchlistFragment.adapter
            setHasFixedSize(true)
        }
        emptyState = TextView(requireContext()).apply {
            text = getString(R.string.watchlist_empty)
            gravity = android.view.Gravity.CENTER
            setPadding(32, 32, 32, 32)
        }
        val listContainer = FrameLayout(requireContext()).apply {
            addView(
                recyclerView,
                FrameLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.MATCH_PARENT,
                ),
            )
            addView(
                emptyState,
                FrameLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.MATCH_PARENT,
                ),
            )
        }
        val root = LinearLayout(requireContext()).apply {
            orientation = LinearLayout.VERTICAL
            addView(
                toolbar,
                LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT,
                ),
            )
            addView(
                listContainer,
                LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    0,
                    1f,
                ),
            )
        }
        ViewCompat.setOnApplyWindowInsetsListener(root) { view, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            view.updatePadding(top = systemBars.top, bottom = systemBars.bottom)
            insets
        }
        ViewCompat.requestApplyInsets(root)
        return root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        (requireActivity() as AppCompatActivity).setSupportActionBar(toolbar)
        (requireActivity() as AppCompatActivity).addMenuProvider(
                object : MenuProvider {
                    override fun onCreateMenu(menu: Menu, menuInflater: MenuInflater) {
                        menuInflater.inflate(R.menu.watchlist_menu, menu)
                        menu.findItem(R.id.watchlist_toggle_layout).title = getString(
                            if (gridLayout) R.string.watchlist_list_view else R.string.watchlist_grid_view,
                        )
                    }

                    override fun onMenuItemSelected(menuItem: MenuItem): Boolean {
                        val sort = when (menuItem.itemId) {
                            R.id.watchlist_sort_name -> WatchlistSort.NAME
                            R.id.watchlist_sort_lowest_price -> WatchlistSort.LOWEST_PRICE
                            R.id.watchlist_sort_highest_price -> WatchlistSort.HIGHEST_PRICE
                            R.id.watchlist_toggle_layout -> {
                                gridLayout = !gridLayout
                                recyclerView.layoutManager = if (gridLayout) {
                                    GridLayoutManager(requireContext(), 2)
                                } else LinearLayoutManager(requireContext())
                                menuItem.title = getString(
                                    if (gridLayout) R.string.watchlist_list_view else R.string.watchlist_grid_view,
                                )
                                return true
                            }
                            else -> return false
                        }
                        adapter.sortBy(sort)
                        return true
                    }
                },
                viewLifecycleOwner,
                Lifecycle.State.RESUMED,
            )
        viewLifecycleOwner.lifecycleScope.launch {
            viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state ->
                    val watched = state.preferences.watchedProductIds
                    adapter.submitProducts(viewModel.products.filter { it.id in watched })
                    recyclerView.contentDescription = if (watched.isEmpty()) {
                        getString(R.string.watchlist_empty)
                    } else {
                        resources.getQuantityString(
                            R.plurals.watched_product_count,
                            watched.size,
                            watched.size,
                        )
                    }
                    emptyState.visibility = if (watched.isEmpty()) View.VISIBLE else View.GONE
                }
            }
        }
    }

    override fun onCreateContextMenu(menu: ContextMenu, view: View, menuInfo: android.view.ContextMenu.ContextMenuInfo?) {
        super.onCreateContextMenu(menu, view, menuInfo)
        requireActivity().menuInflater.inflate(R.menu.watchlist_context_menu, menu)
    }

    override fun onContextItemSelected(item: MenuItem): Boolean {
        val product = contextProduct ?: return super.onContextItemSelected(item)
        return when (item.itemId) {
            R.id.watchlist_context_add -> { viewModel.changeBasket(product.id, 1); true }
            R.id.watchlist_context_remove -> { viewModel.toggleWatched(product.id); true }
            else -> super.onContextItemSelected(item)
        }
    }

    override fun onDestroyView() {
        (activity as? AppCompatActivity)?.setSupportActionBar(null)
        super.onDestroyView()
    }
}

private enum class WatchlistSort { NAME, LOWEST_PRICE, HIGHEST_PRICE }

private class WatchlistAdapter(
    private val onAddToBasket: (Product) -> Unit,
    private val onRemoveFromWatchlist: (Product) -> Unit,
    private val onContextMenu: (View, Product) -> Unit,
) : ListAdapter<Product, WatchlistViewHolder>(ProductDiffCallback) {
    private var sort = WatchlistSort.NAME

    fun submitProducts(products: List<Product>) {
        val sorted = when (sort) {
            WatchlistSort.NAME -> products.sortedBy { it.name }
            WatchlistSort.LOWEST_PRICE -> products.sortedBy { it.lowestPrice.price }
            WatchlistSort.HIGHEST_PRICE -> products.sortedByDescending { it.lowestPrice.price }
        }
        submitList(sorted)
    }

    fun sortBy(sort: WatchlistSort) {
        this.sort = sort
        submitProducts(currentList)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): WatchlistViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.watchlist_product_item, parent, false)
        return WatchlistViewHolder(view, onAddToBasket, onRemoveFromWatchlist, onContextMenu)
    }

    override fun onBindViewHolder(holder: WatchlistViewHolder, position: Int) {
        holder.bind(getItem(position))
    }
}

private class WatchlistViewHolder(
    itemView: View,
    private val onAddToBasket: (Product) -> Unit,
    private val onRemoveFromWatchlist: (Product) -> Unit,
    private val onContextMenu: (View, Product) -> Unit,
) : RecyclerView.ViewHolder(itemView) {
    private val name: TextView = itemView.findViewById(R.id.watchlist_product_name)
    private val price: TextView = itemView.findViewById(R.id.watchlist_product_price)
    private val addButton: Button = itemView.findViewById(R.id.watchlist_add_button)
    private val removeButton: Button = itemView.findViewById(R.id.watchlist_remove_button)
    private var boundProduct: Product? = null

    init {
        itemView.setOnLongClickListener { anchor ->
            val product = boundProduct ?: return@setOnLongClickListener false
            onContextMenu(anchor, product)
            true
        }
    }

    fun bind(product: Product) {
        boundProduct = product
        name.text = itemView.context.getString(
            R.string.watchlist_product_name_size,
            product.name,
            product.size,
        )
        price.text = itemView.context.getString(
            R.string.watchlist_best_price,
            product.lowestPrice.price,
            product.lowestPrice.store,
        )
        addButton.setOnClickListener { onAddToBasket(product) }
        removeButton.setOnClickListener { onRemoveFromWatchlist(product) }
    }
}

private const val STATE_GRID_LAYOUT = "watchlist_grid_layout"

private object ProductDiffCallback : DiffUtil.ItemCallback<Product>() {
    override fun areItemsTheSame(oldItem: Product, newItem: Product): Boolean =
        oldItem.id == newItem.id

    override fun areContentsTheSame(oldItem: Product, newItem: Product): Boolean =
        oldItem == newItem
}

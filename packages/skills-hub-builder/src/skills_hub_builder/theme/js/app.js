// Skills Hub — client-side skill browsing
// Fetches inventory JSON and renders skill cards with filtering.

const filtersContainer = document.querySelector('.filters');
const groupsContainer = document.getElementById('groups-container');

let allData = null;
let activeFilter = 'all';
let repoUrl = '';

async function loadInventory() {
    try {
        const resp = await fetch('inventory/groups.json');
        if (!resp.ok) throw new Error(resp.statusText);
        const index = await resp.json();

        const inventories = await Promise.all(
            index.groups.map(async (g) => {
                const r = await fetch(g.inventory_url);
                if (!r.ok) throw new Error(r.statusText);
                return r.json();
            })
        );

        allData = { index: index.groups, inventories };
        repoUrl = index.repo_url || '';
        buildFilters();
        render();
    } catch (err) {
        groupsContainer.innerHTML =
            '<p class="no-results">Could not load skills inventory.</p>';
        console.error('Inventory load failed:', err);
    }
}

function buildFilters() {
    filtersContainer.innerHTML = '';

    const allBtn = makeFilterBtn('ALL', 'all');
    allBtn.classList.add('active');
    filtersContainer.appendChild(allBtn);

    for (const g of allData.index) {
        filtersContainer.appendChild(
            makeFilterBtn(g.label.toUpperCase(), g.id)
        );
    }
}

function makeFilterBtn(label, value) {
    const btn = document.createElement('button');
    btn.className = 'filter-btn';
    btn.textContent = label;
    btn.dataset.filter = value;
    btn.addEventListener('click', () => {
        document.querySelectorAll('.filter-btn').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        activeFilter = value;
        render();
    });
    return btn;
}

function render() {
    groupsContainer.innerHTML = '';

    const visible = activeFilter === 'all'
        ? allData.inventories
        : allData.inventories.filter((inv) => inv.group === activeFilter);

    if (visible.length === 0) {
        groupsContainer.innerHTML = '<p class="no-results">No skills found.</p>';
        return;
    }

    for (const inv of visible) {
        groupsContainer.appendChild(renderGroup(inv));
    }
}

function renderGroup(inv) {
    const section = document.createElement('div');
    section.className = 'group-section';

    const label = inv.label || inv.group;

    // Meta skill callout
    if (inv.meta_skill) {
        const callout = document.createElement('div');
        callout.className = 'meta-callout';
        const metaStatus = inv.meta_skill.status || 'preview';
        const statusBadge = `<span class="skill-status-badge skill-status-${metaStatus}">${metaStatus.charAt(0).toUpperCase() + metaStatus.slice(1)}</span>`;
        callout.innerHTML = `
            <div class="meta-callout-body">
                <div class="meta-callout-text">
                    <div class="meta-callout-heading">
                        <h3>${label} Pack</h3>
                        ${statusBadge}
                    </div>
                    <p class="meta-desc">${inv.meta_skill.description || inv.description}</p>
                </div>
                <a href="${inv.meta_skill.install_url}" class="btn btn-primary meta-install-btn" download>
                    Install Pack
                </a>
            </div>
        `;
        section.appendChild(callout);
    }

    // Skill cards
    if (inv.skills.length > 0) {
        const grid = document.createElement('div');
        grid.className = 'skills-grid';

        for (const skill of inv.skills) {
            grid.appendChild(renderSkillCard(skill, label));
        }
        section.appendChild(grid);
    }

    return section;
}

function renderSkillCard(skill, groupLabel) {
    const card = document.createElement('div');
    card.className = 'skill-card';

    const status = skill.status || 'preview';
    const statusBadge = `<span class="skill-status-badge skill-status-${status}">${status.charAt(0).toUpperCase() + status.slice(1)}</span>`;
    const editLink = repoUrl && skill.source_path
        ? `<a href="${repoUrl}tree/main/${skill.source_path}" class="edit-link" target="_blank">source</a>` : '';

    card.innerHTML = `
        <div class="skill-header">
            <span class="skill-category">${groupLabel}</span>
            ${statusBadge}
        </div>
        <h3 class="skill-title">${formatTitle(skill.name)}</h3>
        <p class="skill-desc">${truncate(skill.description, 180)}</p>
        <a href="${skill.install_url}" class="download-btn" download>Download .skill</a>
        <div class="card-links">${editLink}</div>
    `;
    return card;
}

function formatTitle(name) {
    return name
        .split('-')
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ');
}

function truncate(str, max) {
    if (!str || str.length <= max) return str || '';
    return str.slice(0, max).replace(/\s+\S*$/, '') + '\u2026';
}

document.addEventListener('DOMContentLoaded', loadInventory);

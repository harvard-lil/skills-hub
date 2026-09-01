// Skills Hub — client-side skill browsing
// Fetches inventory JSON and renders skill cards with filtering.

// Content maturity. Anything that is not `official` is treated as a draft:
// the site would rather understate a skill than overstate one. `preview` is
// the old name for `draft` and still appears in older inventories.
const DRAFT_HINT =
    'Draft — structure is settled enough to read, but the content has not been reviewed or tested.';
const OFFICIAL_HINT = 'Official — reviewed and tested; meant to be used as written.';

function normalizeStatus(status) {
    return (status || '').toLowerCase() === 'official' ? 'official' : 'draft';
}

function statusBadge(status) {
    const s = normalizeStatus(status);
    const label = s === 'official' ? 'Official' : 'Draft';
    const hint = s === 'official' ? OFFICIAL_HINT : DRAFT_HINT;
    return `<span class="skill-status-badge skill-status-${s}" title="${hint}">${label}</span>`;
}

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

    const notice = draftNotice(visible);
    if (notice) groupsContainer.appendChild(notice);

    for (const inv of visible) {
        groupsContainer.appendChild(renderGroup(inv));
    }
}

// When nothing on view is official, per-card contrast has nothing to work
// against, so the state is stated once at the top instead.
function draftNotice(inventories) {
    const statuses = [];
    for (const inv of inventories) {
        if (inv.meta_skill) statuses.push(normalizeStatus(inv.meta_skill.status));
        for (const s of inv.skills) statuses.push(normalizeStatus(s.status));
    }
    if (statuses.length === 0 || statuses.some((s) => s === 'official')) return null;

    const el = document.createElement('div');
    el.className = 'hub-notice';
    el.innerHTML = `
        <strong>Everything here is a draft.</strong>
        These skills are published to show what a skill looks like and how the hub
        works. The instructions inside them have not been reviewed or tested, so read
        them for their shape rather than following them as guidance.
    `;
    return el;
}

function renderGroup(inv) {
    const section = document.createElement('div');
    section.className = 'group-section';

    const label = inv.label || inv.group;

    // Meta skill callout
    if (inv.meta_skill) {
        const callout = document.createElement('div');
        callout.className = 'meta-callout';
        const metaStatus = normalizeStatus(inv.meta_skill.status);
        const isDraft = metaStatus !== 'official';
        if (isDraft) callout.classList.add('is-draft');
        const viewLink = inv.meta_skill.page_url
            ? `<a href="${inv.meta_skill.page_url}" class="btn ${isDraft ? 'btn-quiet' : 'btn-secondary'} meta-view-btn">Read Pack</a>`
            : '';
        callout.innerHTML = `
            <div class="meta-callout-body">
                <div class="meta-callout-text">
                    <div class="meta-callout-heading">
                        <h3>${label} Pack</h3>
                        ${statusBadge(metaStatus)}
                    </div>
                    <p class="meta-desc">${inv.meta_skill.description || inv.description}</p>
                </div>
                <div class="meta-callout-actions">
                    ${viewLink}
                    <a href="${inv.meta_skill.install_url}" class="btn ${isDraft ? 'btn-outline-muted' : 'btn-primary'} meta-install-btn" download>
                        Install Pack
                    </a>
                </div>
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

    const status = normalizeStatus(skill.status);
    const isDraft = status !== 'official';
    if (isDraft) card.classList.add('is-draft');

    const editLink = repoUrl && skill.source_path
        ? `<a href="${repoUrl}tree/main/${skill.source_path}" class="edit-link" target="_blank">source</a>` : '';

    // A draft leads with reading and a finished skill leads with installing:
    // the emphasis says which one the hub is asking to be taken seriously.
    const readBtn = skill.page_url
        ? `<a href="${skill.page_url}" class="card-btn ${isDraft ? 'card-btn-quiet' : 'card-btn-secondary'}">Read skill</a>`
        : '';
    const downloadBtn = `<a href="${skill.install_url}" class="card-btn ${isDraft ? 'card-btn-secondary' : 'card-btn-primary'}" download>Download .skill</a>`;


    card.innerHTML = `
        <div class="skill-header">
            <span class="skill-category">${groupLabel}</span>
            ${statusBadge(status)}
        </div>
        <h3 class="skill-title">${formatTitle(skill.name)}</h3>
        <p class="skill-desc">${truncate(skill.description, 180)}</p>
        <div class="card-actions">${readBtn}${downloadBtn}</div>
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

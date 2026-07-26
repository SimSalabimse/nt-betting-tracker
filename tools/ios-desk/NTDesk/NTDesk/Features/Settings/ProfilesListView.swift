import SwiftUI

/// Manage saved connection profiles: add, set default, delete.
/// Stack-free: push target inside Settings sheet NavigationStack.
struct ProfilesListView: View {
    @EnvironmentObject private var sync: SyncService
    @State private var showAdd = false
    @State private var newName: String = ""
    @State private var newURL: String = ""

    var body: some View {
        List {
            Section {
                ForEach(sync.profiles) { profile in
                    Button {
                        sync.setDefaultProfile(id: profile.id)
                    } label: {
                        HStack(alignment: .top, spacing: DeskSpacing.s2) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(profile.name)
                                    .font(.body.weight(.semibold))
                                    .foregroundStyle(DeskTheme.text)
                                Text(profile.baseURLString)
                                    .font(.caption.monospaced())
                                    .foregroundStyle(DeskTheme.textMuted)
                                    .lineLimit(2)
                            }
                            Spacer(minLength: DeskSpacing.s2)
                            if profile.isDefault {
                                Text("Default")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(DeskTheme.accent)
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 4)
                                    .background(DeskTheme.accent.opacity(0.15))
                                    .clipShape(Capsule())
                            }
                        }
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("\(profile.name), \(profile.isDefault ? "default" : "not default")")
                    .accessibilityHint("Sets this profile as the default connection")
                    .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                        if sync.profiles.count > 1 {
                            Button(role: .destructive) {
                                sync.removeProfile(id: profile.id)
                            } label: {
                                Label("Delete", systemImage: "trash")
                            }
                        }
                    }
                }
            } header: {
                Text("Profiles")
            } footer: {
                Text("Tap a profile to make it the default. Save & sync uses the default URL. Legacy Settings still edits the same default via base URL.")
                    .font(.caption)
            }
        }
        .scrollContentBackground(.hidden)
        .background(DeskTheme.bg)
        .navigationTitle("Profiles")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    newName = ""
                    newURL = sync.baseURLString
                    showAdd = true
                } label: {
                    Image(systemName: "plus")
                }
                .accessibilityLabel("Add profile")
            }
        }
        .sheet(isPresented: $showAdd) {
            NavigationStack {
                Form {
                    Section {
                        TextField("Name", text: $newName)
                            .foregroundStyle(DeskTheme.text)
                        TextField("http://192.168.x.x:8787", text: $newURL)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .keyboardType(.URL)
                            .textContentType(.URL)
                            .foregroundStyle(DeskTheme.text)
                    } header: {
                        Text("New profile")
                    }
                }
                .scrollContentBackground(.hidden)
                .background(DeskTheme.bg)
                .navigationTitle("Add profile")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("Cancel") { showAdd = false }
                    }
                    ToolbarItem(placement: .confirmationAction) {
                        Button("Add") {
                            let url = newURL.trimmingCharacters(in: .whitespacesAndNewlines)
                            guard !url.isEmpty else { return }
                            let name = newName.trimmingCharacters(in: .whitespacesAndNewlines)
                            sync.addProfile(
                                name: name.isEmpty
                                    ? ConnectionProfileStore.displayName(for: url)
                                    : name,
                                baseURLString: url,
                                makeDefault: true
                            )
                            showAdd = false
                        }
                        .disabled(newURL.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                    }
                }
            }
        }
    }
}
